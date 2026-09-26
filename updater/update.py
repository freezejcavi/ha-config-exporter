from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

VERSION = "0.1.0"

SOURCE_REPOSITORY = "git@github.com:freezejcavi/ha-config-exporter.git"
SOURCE_BRANCH = "main"
TARGET_PATH = Path("/addons/ha-config-exporter")
TARGET_APP_SLUG = "local_ha_config_exporter"

DATA_DIR = Path("/data")
SSH_DIR = DATA_DIR / "ssh"
KEY_PATH = SSH_DIR / "id_ed25519"
KNOWN_HOSTS_PATH = SSH_DIR / "known_hosts"

RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
RUN_LINE = "#" * 72


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def emit(level: str, message: object, color: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    for line in str(message).splitlines() or [""]:
        print(
            f"{color}[{timestamp()}] {level:<6} {line}{RESET}",
            file=stream,
            flush=True,
        )


def info(message: object) -> None:
    emit("INFO", message, CYAN)


def warn(message: object) -> None:
    emit("WARN", message, YELLOW)


def ok(message: object) -> None:
    emit("OK", message, GREEN)


def error(message: object) -> None:
    emit("ERROR", message, RED, error=True)


def header(title: str) -> None:
    print(f"{MAGENTA}{RUN_LINE}{RESET}", flush=True)
    print(f"{MAGENTA}### {timestamp()} | {title}{RESET}", flush=True)
    print(f"{MAGENTA}{RUN_LINE}{RESET}", flush=True)


def footer(title: str, *, success: bool) -> None:
    color = GREEN if success else RED
    print(f"{color}{RUN_LINE}{RESET}", flush=True)
    print(f"{color}### {timestamp()} | {title}{RESET}", flush=True)
    print(f"{color}{RUN_LINE}{RESET}", flush=True)


def run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
        env=merged,
    )


def ensure_ssh_material() -> bool:
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    created = False

    if not KEY_PATH.exists():
        run(
            "ssh-keygen",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "ha-config-exporter-updater@home-assistant",
            "-f",
            str(KEY_PATH),
        )
        created = True

    KEY_PATH.chmod(0o600)

    if not KNOWN_HOSTS_PATH.exists():
        with urllib.request.urlopen(
            "https://api.github.com/meta",
            timeout=20,
        ) as response:
            meta = json.load(response)

        keys = meta.get("ssh_keys") or []
        if not keys:
            raise RuntimeError("GitHub metadata did not return SSH host keys")

        KNOWN_HOSTS_PATH.write_text(
            "".join(f"github.com {key}\n" for key in keys),
            encoding="utf-8",
        )
        KNOWN_HOSTS_PATH.chmod(0o600)

    return created


def public_key() -> str:
    return KEY_PATH.with_suffix(".pub").read_text(encoding="utf-8").strip()


def git_env() -> dict[str, str]:
    return {
        "GIT_SSH_COMMAND": (
            f"ssh -i {KEY_PATH} -o IdentitiesOnly=yes "
            f"-o UserKnownHostsFile={KNOWN_HOSTS_PATH} "
            "-o StrictHostKeyChecking=yes"
        )
    }


def verify_remote_access() -> bool:
    result = run(
        "git",
        "ls-remote",
        "--heads",
        SOURCE_REPOSITORY,
        SOURCE_BRANCH,
        check=False,
        env=git_env(),
    )
    if result.returncode == 0:
        return True

    warn("Source repository access is not configured yet.")
    info("Add this public key to freezejcavi/ha-config-exporter as a read-only Deploy Key:")
    info(public_key())
    return False


def read_app_version(path: Path) -> str:
    config_path = path / "config.yaml"
    content = config_path.read_text(encoding="utf-8")
    match = re.search(r"^version:\s*['\"]?([^'\"\s]+)", content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Cannot read version from {config_path}")
    return match.group(1)


def supervisor_request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    *,
    timeout: int = 900,
) -> dict[str, object]:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN is unavailable")

    body = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"http://supervisor{path}",
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Supervisor API {method} {path} failed: HTTP {err.code}: {detail}"
        ) from err

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}

    if isinstance(parsed, dict) and parsed.get("result") == "error":
        raise RuntimeError(
            f"Supervisor API {method} {path} failed: {parsed.get('message', parsed)}"
        )

    return parsed if isinstance(parsed, dict) else {"data": parsed}


def main() -> int:
    header(f"HA Config Exporter Updater {VERSION} — RUN START")

    try:
        created = ensure_ssh_material()
        if created:
            info("Generated dedicated read-only source Deploy Key.")

        if not verify_remote_access():
            ok("Bootstrap complete — add the Deploy Key, then run the updater again.")
            footer(
                f"HA Config Exporter Updater {VERSION} — RUN END: SETUP REQUIRED",
                success=True,
            )
            return 0

        if not (TARGET_PATH / ".git").is_dir():
            raise RuntimeError(
                f"Expected exporter Git checkout not found at {TARGET_PATH}"
            )

        dirty = run(
            "git",
            "status",
            "--porcelain",
            cwd=TARGET_PATH,
        ).stdout.strip()
        if dirty:
            raise RuntimeError(
                "Exporter source checkout contains local modifications; "
                "automatic update refused."
            )

        old_sha = run("git", "rev-parse", "HEAD", cwd=TARGET_PATH).stdout.strip()
        old_version = read_app_version(TARGET_PATH)

        run(
            "git",
            "remote",
            "set-url",
            "origin",
            SOURCE_REPOSITORY,
            cwd=TARGET_PATH,
        )
        run(
            "git",
            "fetch",
            "--prune",
            "origin",
            SOURCE_BRANCH,
            cwd=TARGET_PATH,
            env=git_env(),
        )

        remote_ref = f"origin/{SOURCE_BRANCH}"
        new_sha = run("git", "rev-parse", remote_ref, cwd=TARGET_PATH).stdout.strip()

        if new_sha == old_sha:
            ok(f"Exporter already current: {old_version} ({old_sha[:8]})")
            footer(
                f"HA Config Exporter Updater {VERSION} — RUN END: NO UPDATE",
                success=True,
            )
            return 0

        ancestry = run(
            "git",
            "merge-base",
            "--is-ancestor",
            old_sha,
            new_sha,
            cwd=TARGET_PATH,
            check=False,
        )
        if ancestry.returncode != 0:
            raise RuntimeError(
                "Remote source is not a fast-forward of the local checkout; "
                "automatic update refused."
            )

        run("git", "reset", "--hard", new_sha, cwd=TARGET_PATH)
        new_version = read_app_version(TARGET_PATH)

        info(f"Source updated: {old_sha[:8]} -> {new_sha[:8]}")

        supervisor_request("POST", "/store/reload", {})
        info("Supervisor store reloaded.")

        if new_version == old_version:
            ok(
                f"Source changed, exporter version remains {new_version}; "
                "no image update required."
            )
            footer(
                f"HA Config Exporter Updater {VERSION} — RUN END: SOURCE UPDATED",
                success=True,
            )
            return 0

        info(f"Updating exporter: {old_version} -> {new_version}")
        supervisor_request(
            "POST",
            f"/store/apps/{TARGET_APP_SLUG}/update",
            {"backup": False, "background": False},
            timeout=1200,
        )
        ok(f"HA Config Exporter updated to {new_version}")

        footer(
            f"HA Config Exporter Updater {VERSION} — RUN END: SUCCESS",
            success=True,
        )
        return 0

    except Exception as err:  # noqa: BLE001 - top-level App boundary
        error(f"{type(err).__name__}: {err}")
        footer(
            f"HA Config Exporter Updater {VERSION} — RUN END: ERROR",
            success=False,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
