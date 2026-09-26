from __future__ import annotations

import json
import sys
from pathlib import Path

from config import load_config
from gitmirror import ensure_ssh_material, prepare_repository, public_key, publish_snapshot
from selector import build_mirror


def main() -> int:
    print("HA Config Exporter 0.1.0-dev.1")
    print("Purpose: one-way Home Assistant configuration mirror for ChatGPT audit/guidance")

    config = load_config()

    key_created = ensure_ssh_material()
    if key_created:
        print("Generated a dedicated SSH deploy key for the target mirror repository:")
        print(public_key())
        print(
            "Add the public key above to the target GitHub repository as a write-enabled Deploy Key."
        )

    try:
        repository, expected_sha = prepare_repository(config.repository)
    except PermissionError as err:
        print(str(err), file=sys.stderr)
        return 2

    print(f"Remote baseline: {expected_sha}")

    stats = build_mirror(
        repository,
        exclude=config.exclude,
        include=config.include,
    )

    print(
        "Prepared managed mirror: "
        f"{stats['files']} file copies, {stats['symlinks']} symlinks"
    )

    result = publish_snapshot(
        repository,
        config=config.repository,
        expected_remote_sha=expected_sha,
        dry_run=config.dry_run,
    )

    print(json.dumps(result, indent=2, sort_keys=True))

    if not result["changed"]:
        print("Mirror is unchanged; no commit or push required.")
        return 0

    if config.dry_run:
        print("Dry run: snapshot differs, but no push was performed.")
        return 0

    print(f"Published root snapshot: {result['snapshot_sha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
