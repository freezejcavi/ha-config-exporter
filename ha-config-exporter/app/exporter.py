from __future__ import annotations

from config import load_config
from gitmirror import (
    ensure_ssh_material,
    prepare_repository,
    public_key,
    publish_snapshot,
)
from logutil import changes, error, footer, header, info, ok
from selector import build_mirror

VERSION = "0.1.0-dev.7"


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

        stats = build_mirror(
            repository,
            homeassistant=config.homeassistant,
            addon_configs=config.addon_configs,
        )
        info(
            f"Mirror prepared: {stats['files']} files, "
            f"{stats['symlinks']} symlinks"
        )

        result = publish_snapshot(
            repository,
            config=config.repository,
            expected_remote_sha=expected_sha,
            dry_run=config.dry_run,
        )
        changed_files = result.get("changed_files", [])
        if isinstance(changed_files, list) and changed_files:
            changes([str(item) for item in changed_files])

        if not result["changed"]:
            ok("No changes detected — nothing pushed.")
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

        snapshot = str(result["snapshot_sha"])
        ok(f"GitHub snapshot published: {snapshot[:8]}")
        footer(
            f"HA Config Exporter {VERSION} — RUN END: SUCCESS",
            success=True,
        )
        return 0

    except (PermissionError, RuntimeError, TypeError, ValueError) as err:
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
