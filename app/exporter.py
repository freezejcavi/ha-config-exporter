from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from config import load_config
from gitmirror import (
    ensure_ssh_material,
    prepare_repository,
    public_key,
    publish_snapshot,
)
from selector import build_mirror


VERSION = "0.1.0-dev.2"


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def log(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(f"[{timestamp()}] {message}", file=stream, flush=True)


def main() -> int:
    log("=" * 72)
    log(f"HA Config Exporter {VERSION} — RUN START")
    log("Purpose: one-way Home Assistant configuration mirror for ChatGPT audit/guidance")

    config = load_config()

    key_created = ensure_ssh_material()
    if key_created:
        log("Generated a dedicated SSH deploy key for the target mirror repository:")
        log(public_key())
        log(
            "Add the public key above to the target GitHub repository "
            "as a write-enabled Deploy Key."
        )

    try:
        repository, expected_sha = prepare_repository(config.repository)
    except PermissionError as err:
        log(str(err), error=True)
        log(f"HA Config Exporter {VERSION} — RUN END: ERROR", error=True)
        log("=" * 72, error=True)
        return 2

    log(f"Remote baseline: {expected_sha}")

    stats = build_mirror(
        repository,
        exclude=config.exclude,
        include=config.include,
    )

    log(
        "Prepared managed mirror: "
        f"{stats['files']} file copies, {stats['symlinks']} symlinks"
    )

    result = publish_snapshot(
        repository,
        config=config.repository,
        expected_remote_sha=expected_sha,
        dry_run=config.dry_run,
    )

    log(json.dumps(result, indent=2, sort_keys=True))

    if not result["changed"]:
        log("Mirror is unchanged; no commit or push required.")
        log(f"HA Config Exporter {VERSION} — RUN END: SUCCESS / NO CHANGE")
        log("=" * 72)
        return 0

    if config.dry_run:
        log("Dry run: snapshot differs, but no push was performed.")
        log(f"HA Config Exporter {VERSION} — RUN END: SUCCESS / DRY RUN")
        log("=" * 72)
        return 0

    log(f"Published root snapshot: {result['snapshot_sha']}")
    log(f"HA Config Exporter {VERSION} — RUN END: SUCCESS")
    log("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
