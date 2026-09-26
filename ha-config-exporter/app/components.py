from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

FULL_SOURCE_COMPONENTS = frozenset(
    {
        "anime_benchmark",
        "battery_health",
    }
)

HASH_IGNORED_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
    }
)

HASH_IGNORED_SUFFIXES = frozenset(
    {
        ".pyc",
        ".pyo",
    }
)


def _github_repository_url(*values: object) -> str | None:
    fallback: str | None = None

    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue

        candidate = value.strip()
        if fallback is None:
            fallback = candidate

        parsed = urlsplit(candidate)
        if (parsed.hostname or "").lower() != "github.com":
            continue

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            continue

        owner = parts[0]
        repository = parts[1].removesuffix(".git")
        return f"https://github.com/{owner}/{repository}"

    return fallback


def _hash_component_tree(root: Path) -> str:
    digest = hashlib.sha256()

    for current, directories, filenames in os.walk(root, topdown=True):
        current_path = Path(current)

        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in HASH_IGNORED_DIRS
        )

        for directory in tuple(directories):
            path = current_path / directory
            if not path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            digest.update(b"L\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
            digest.update(b"\0")
            directories.remove(directory)

        for filename in sorted(filenames):
            path = current_path / filename
            if path.suffix.lower() in HASH_IGNORED_SUFFIXES:
                continue

            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                digest.update(b"L\0")
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                digest.update(
                    os.readlink(path).encode("utf-8", errors="surrogateescape")
                )
                digest.update(b"\0")
                continue

            digest.update(b"F\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")

    return digest.hexdigest()


def _read_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _component_record(
    manifest: dict[str, object],
    *,
    component_root: str,
    relative_path: str,
    tree_hash: str,
) -> dict[str, object]:
    issue_tracker = manifest.get("issue_tracker")
    documentation = manifest.get("documentation")

    return {
        "component_root": component_root,
        "documentation": documentation,
        "export_mode": (
            "full_source"
            if component_root in FULL_SOURCE_COMPONENTS
            else "metadata_only"
        ),
        "installed_tree_sha256": tree_hash,
        "integration_type": manifest.get("integration_type"),
        "name": manifest.get("name"),
        "path": relative_path,
        "requirements": (
            manifest.get("requirements")
            if isinstance(manifest.get("requirements"), list)
            else []
        ),
        "source": _github_repository_url(issue_tracker, documentation),
        "version": manifest.get("version"),
    }


def write_component_index(
    repository_root: Path,
    *,
    source_root: Path = Path("/homeassistant/custom_components"),
) -> int:
    if not source_root.exists():
        return 0

    components: dict[str, dict[str, object]] = {}
    links: dict[str, dict[str, str]] = {}

    for entry in sorted(source_root.iterdir(), key=lambda item: item.name.casefold()):
        if entry.is_symlink():
            target = os.readlink(entry)
            links[entry.name] = {
                "target": target,
                "target_sha256": hashlib.sha256(
                    target.encode("utf-8", errors="surrogateescape")
                ).hexdigest(),
            }
            continue

        if not entry.is_dir():
            continue

        tree_hash = _hash_component_tree(entry)
        manifests = sorted(
            entry.rglob("manifest.json"),
            key=lambda path: path.as_posix().casefold(),
        )

        for manifest_path in manifests:
            manifest = _read_manifest(manifest_path)
            domain_value = manifest.get("domain")
            if not isinstance(domain_value, str) or not domain_value.strip():
                continue

            domain = domain_value.strip()
            relative_path = manifest_path.parent.relative_to(source_root).as_posix()
            components[domain] = _component_record(
                manifest,
                component_root=entry.name,
                relative_path=relative_path,
                tree_hash=tree_hash,
            )

    payload = {
        "components": components,
        "links": links,
        "schema_version": 1,
    }

    destination = repository_root / "derived" / "custom_components" / "index.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 1
