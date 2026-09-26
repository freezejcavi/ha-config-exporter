from __future__ import annotations

import json

from config import load_config
from gitmirror import (
    ensure_ssh_material,
    prepare_repository,
    public_key,
    publish_snapshot,
)
from logutil import error, footer, header, info, ok
from selector import build_mirror

VERSION = "0.1.0-dev.2"


def main() -> int:
    header(f"HA Config Exporter {VERSION} — RUN START")
    info("One-way Home Assistant configuration mirror for ChatGPT audit/guidance")

    try:
        config = load_config()

        key_created = ensure_ssh_material()
        if key_created:
            info("Generated a dedicated SSH deploy key for the target mirror repository:")
            info(public_key())
            info(
                "Add the public key above to the target GitHub repository "
                "as a write-enabled Deploy Key."
            )

        repository, expected_sha = prepare_repository(config.repository)
        info(f"Remote baseline: {expected_sha}")

        stats = build_mirror(
            repository,
            exclude=config.exclude,
            include=config.include,
        )
        info(
            "Prepared managed mirror: "
            f"{stats['files']} file copies, {stats['symlinks']} symlinks"
        )

        result = publish_snapshot(
            repository,
            config=config.repository,
            expected_remote_sha=expected_sha,
            dry_run=config.dry_run,
        )
        info(json.dumps(result, indent=2, sort_keys=True))

        if not result["changed"]:
            ok("Mirror unchanged — no commit or push required.")
            footer(
                f"HA Config Exporter {VERSION} — RUN END: SUCCESS / NO CHANGE",
                success=True,
            )
            return 0

        if config.dry_run:
            ok("Dry run complete — snapshot differs, no push performed.")
            footer(
                f"HA Config Exporter {VERSION} — RUN END: SUCCESS / DRY RUN",
                success=True,
            )
            return 0

        ok(f"Published root snapshot: {result['snapshot_sha']}")
        footer(
            f"HA Config Exporter {VERSION} — RUN END: SUCCESS",
            success=True,
        )
        return 0

    except (PermissionError, RuntimeError, ValueError) as err:
        error(err)
        footer(
            f"HA Config Exporter {VERSION} — RUN END: ERROR",
            success=False,
        )
        return 2
    except Exception as err:  # noqa: BLE001 - top-level App boundary logs cleanly
        error(f"Unexpected {type(err).__name__}: {err}")
        footer(
            f"HA Config Exporter {VERSION} — RUN END: ERROR",
            success=False,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
