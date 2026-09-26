from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
from collections.abc import Iterable
from pathlib import Path

from config import ScopeConfig
from logutil import warn

SOURCE_ROOTS = (
    Path("/homeassistant"),
    Path("/addon_configs"),
)

BASE_EXCLUDE_PATTERNS = {
    "homeassistant": (
        "*.db",
        "*.db-shm",
        "*.db-wal",
        "*.log*",
        "*.gz",
        "**/__pycache__",
        "**/__pycache__/**",
        "**/._*",
        "**/.DS_Store",
        "**/deps",
        "**/deps/**",
        "known_devices.yaml",
        "tts",
        "tts/**",
        "zigbee2mqtt/coordinator_backup.json",
        "zigbee2mqtt/state.json",
        "zigbee2mqtt/device_icons",
        "zigbee2mqtt/device_icons/**",
        "ml_weather/data",
        "ml_weather/data/**",
        "ml_weather/output",
        "ml_weather/output/**",
        "ml_weather/models",
        "ml_weather/models/**",
        ".cache",
        ".cache/**",
        ".ha_run.lock",
        "codex_input",
        "codex_input/**",
        "image",
        "image/**",
        "www/codex_cli_auth",
        "www/codex_cli_auth/**",
        "www/community",
        "www/community/**",
        "www/calendars",
        "www/calendars/**",
        "codex_tasks",
        "codex_tasks/**",
    ),
    "addon_configs": (
        "**/__pycache__",
        "**/__pycache__/**",
        "**/node_modules",
        "**/node_modules/**",
        "**/*.backup",
    ),
}

BASE_INCLUDE_PATTERNS = {
    "homeassistant": (
        "codex_tasks/*/task.json",
    ),
    "addon_configs": (),
}

MANAGED_DESTINATIONS = (
    "homeassistant",
    "addon_configs",
    "derived",
)

STORAGE_DEFAULT_ALLOW = (
    "/homeassistant/.storage/core.*registry",
    "/homeassistant/.storage/lovelace*",
    "/homeassistant/.storage/zone",
)

HARD_DENY_PATTERNS = (
    "*/.git",
    "*/.git/**",
    "*/secrets.yaml",
    "*/secret.yaml",
    "*/flows_cred.json",
    "*/flows_cred*.json",
    "*/.storage/auth",
    "*/.storage/auth.*",
    "*/.storage/auth_provider.homeassistant",
    "*/.storage/core.config_entries",
    "*/.storage/application_credentials",
    "*/.storage/cloud",
    "/homeassistant/.cloud",
    "/homeassistant/.cloud/**",
    "*/flows_cred*",
    "*/.config.users.json*",
    "*/credentials.json",
    "*/credentials.*",
    "*/*.pem",
    "*/*.key",
    "*/id_rsa*",
    "*/id_ed25519*",
)

SENSITIVE_KEY = re.compile(
    r"^(?:password|passwd|token|api_key|apikey|client_secret|credential_secret|"
    r"access_token|refresh_token|private_key|ssh_key|github_token)$",
    re.IGNORECASE,
)

HIGH_RISK_TEXT = (
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]+\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

TEXT_CONFIG_SUFFIXES = {
    ".yaml",
    ".yml",
    ".json",
    ".conf",
    ".ini",
    ".toml",
}


def source_path(path: Path) -> str:
    return "/" + path.as_posix().lstrip("/")


def normalize_pattern(pattern: str) -> str:
    value = pattern.strip().replace("\\", "/")
    if not value.startswith("/"):
        value = "/" + value
    return value


def matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for raw in patterns:
        pattern = normalize_pattern(raw)
        if pattern.endswith("/") and (
            normalized == pattern[:-1] or normalized.startswith(pattern)
        ):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def normalize_relative_pattern(pattern: str) -> str:
    return pattern.strip().replace("\\", "/").lstrip("/")


def matches_relative(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    for raw in patterns:
        pattern = normalize_relative_pattern(raw)
        if not pattern:
            continue
        if pattern == "**":
            return True
        if pattern.endswith("/") and (
            normalized == pattern[:-1] or normalized.startswith(pattern)
        ):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def is_hard_denied(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return matches(normalized, HARD_DENY_PATTERNS)


def storage_default_allowed(path: str) -> bool:
    if not path.startswith("/homeassistant/.storage/"):
        return True
    return matches(path, STORAGE_DEFAULT_ALLOW)


def is_probably_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def should_copy(
    absolute_source: str,
    relative_source: str,
    source: Path,
    *,
    scope_name: str,
    scope: ScopeConfig,
) -> bool:
    if is_hard_denied(absolute_source):
        return False

    base_excluded = (
        not storage_default_allowed(absolute_source)
        or matches_relative(relative_source, BASE_EXCLUDE_PATTERNS[scope_name])
    )
    base_included = matches_relative(
        relative_source,
        BASE_INCLUDE_PATTERNS[scope_name],
    )
    allowed = not base_excluded or base_included

    if matches_relative(relative_source, scope.exclude):
        allowed = False

    if matches_relative(relative_source, scope.include):
        allowed = True

    if not allowed:
        return False

    return not (source.is_file() and is_probably_binary(source))



def _copy_symlink(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    os.symlink(os.readlink(source), destination)


def copy_root(
    source_root: Path,
    destination_root: Path,
    *,
    scope: ScopeConfig,
) -> tuple[int, int]:
    files = 0
    symlinks = 0
    scope_name = source_root.name

    def walk(source_dir: Path, destination_dir: Path) -> None:
        nonlocal files, symlinks
        for entry in os.scandir(source_dir):
            source = Path(entry.path)
            absolute = source_path(source)
            relative = source.relative_to(source_root).as_posix()
            destination = destination_dir / entry.name

            if is_hard_denied(absolute):
                continue

            if entry.is_symlink():
                if should_copy(
                    absolute,
                    relative,
                    source,
                    scope_name=scope_name,
                    scope=scope,
                ):
                    _copy_symlink(source, destination)
                    symlinks += 1
                continue

            if entry.is_dir(follow_symlinks=False):
                walk(source, destination)
                continue

            if not entry.is_file(follow_symlinks=False):
                continue

            if should_copy(
                absolute,
                relative,
                source,
                scope_name=scope_name,
                scope=scope,
            ):
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                files += 1

    walk(source_root, destination_root)
    return files, symlinks


def sanitize_zigbee2mqtt_configuration(destination_repository: Path) -> None:
    path = destination_repository / "homeassistant" / "zigbee2mqtt" / "configuration.yaml"
    if not path.exists():
        return

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    result: list[str] = []
    section: str | None = None
    skip_block_indent: int | None = None

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if skip_block_indent is not None:
            if stripped and indent > skip_block_indent:
                continue
            skip_block_indent = None

        if indent == 0 and stripped.endswith(":") and not stripped.startswith(("#", "-")):
            section = stripped[:-1].strip()

        key_match = re.match(r"^(\s*)([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        if not key_match:
            result.append(line)
            continue

        prefix, key, _value = key_match.groups()

        if section == "mqtt" and key == "password":
            result.append(f'{prefix}password: "<redacted>"')
            continue

        if section == "advanced" and key == "network_key":
            result.append(f'{prefix}network_key: "<redacted>"')
            skip_block_indent = len(prefix)
            continue

        result.append(line)

    path.write_text("\n".join(result) + "\n", encoding="utf-8")


def write_sanitized_secrets(destination_repository: Path) -> None:
    source = Path("/homeassistant/secrets.yaml")
    destination = destination_repository / "homeassistant" / "secrets.yaml"

    if not source.exists():
        destination.unlink(missing_ok=True)
        return

    result: list[str] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            result.append(line)
            continue

        prefix, _value = line.split(":", 1)
        indent = prefix[: len(prefix) - len(prefix.lstrip())]
        key = prefix.strip()
        result.append(f'{indent}{key}: ""')

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(result) + "\n", encoding="utf-8")


def _value_is_safe(value: object) -> bool:
    if value is None or value is False or value == "":
        return True
    if isinstance(value, str):
        normalized = value.strip()
        return (
            not normalized
            or normalized.startswith("!secret")
            or normalized in {"<redacted>", "null", "~", '""', "''"}
        )
    return not isinstance(value, (dict, list))


def _json_sensitive_values(value: object, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            location = f"{prefix}.{key_text}" if prefix else key_text
            if SENSITIVE_KEY.match(key_text) and not _value_is_safe(child):
                findings.append(location)
            findings.extend(_json_sensitive_values(child, location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_json_sensitive_values(child, f"{prefix}[{index}]"))
    return findings


def _should_scan_config_file(path: Path, repository_root: Path) -> bool:
    relative = path.relative_to(repository_root).as_posix()
    suffix = path.suffix.lower()

    if relative.startswith("addon_configs/") and path.name == "flows.json":
        return False

    if relative.startswith("addon_configs/"):
        return suffix in TEXT_CONFIG_SUFFIXES

    if not relative.startswith("homeassistant/"):
        return False

    if relative.startswith(("homeassistant/custom_components/", "homeassistant/www/")):
        return False

    if "/.storage/" in "/" + relative:
        return True

    return suffix in TEXT_CONFIG_SUFFIXES


def scan_for_secrets(repository_root: Path) -> None:
    failures: list[str] = []

    for path in repository_root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        relative = path.relative_to(repository_root).as_posix()

        for pattern in HIGH_RISK_TEXT:
            if pattern.search(text):
                failures.append(f"{relative}: high-risk token/private-key signature")
                break

        if not _should_scan_config_file(path, repository_root):
            continue

        if path.suffix.lower() == ".json" or "/.storage/" in "/" + relative:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
            if data is not None:
                for location in _json_sensitive_values(data):
                    failures.append(f"{relative}: sensitive value at {location}")
                continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.*?)\s*$", line)
            if not match or not SENSITIVE_KEY.match(match.group(1)):
                continue
            raw_value = match.group(2).strip().strip('"').strip("'")
            if raw_value and not raw_value.startswith("!secret") and raw_value != "<redacted>":
                failures.append(
                    f"{relative}:{line_number}: non-redacted {match.group(1)}"
                )

    if failures:
        preview = "\n".join(f"  - {item}" for item in failures[:30])
        more = "" if len(failures) <= 30 else f"\n  ... and {len(failures) - 30} more"
        raise RuntimeError(
            "Security scan blocked export because potential secrets were found:\n"
            + preview
            + more
        )


def remove_managed_roots(repository_root: Path) -> None:
    for name in MANAGED_DESTINATIONS:
        target = repository_root / name
        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
        elif target.exists():
            shutil.rmtree(target)


def build_mirror(
    repository_root: Path,
    *,
    homeassistant: ScopeConfig,
    addon_configs: ScopeConfig,
) -> dict[str, int]:
    remove_managed_roots(repository_root)

    stats = {"files": 0, "symlinks": 0}
    scopes = {
        "homeassistant": homeassistant,
        "addon_configs": addon_configs,
    }

    for source_root in SOURCE_ROOTS:
        if not source_root.exists():
            warn(f"Source root unavailable: {source_root}")
            continue

        destination_root = repository_root / source_root.name
        destination_root.mkdir(parents=True, exist_ok=True)
        copied_files, copied_links = copy_root(
            source_root,
            destination_root,
            scope=scopes[source_root.name],
        )
        stats["files"] += copied_files
        stats["symlinks"] += copied_links

    write_sanitized_secrets(repository_root)
    sanitize_zigbee2mqtt_configuration(repository_root)
    scan_for_secrets(repository_root)
    return stats
