# Changelog

## 0.1.0

- Promote the accepted dev.9 analytical mirror contract to stable.
- Remove the development test repository from packaged defaults.
- Require an explicit GitHub SSH mirror target for fresh installations.
- Preserve the validated lean custom-component provenance model, Codex task records, deterministic no-change behavior, Supervisor App metadata, and Node-RED allowlist.


## 0.1.0-dev.9

- Restore `codex_tasks/*/task.json` to the analytical mirror.
- Switch third-party custom integrations to metadata-only export.
- Keep full source for locally developed `battery_health` and `anime_benchmark`.
- Add `derived/custom_components/index.json` with version, upstream source, requirements and an installed-tree SHA-256 fingerprint.
- Exclude generic `node_modules` and backup artifacts from the Home Assistant scope.
- Keep canonical component metadata, YAML descriptors and EN/CS translations for third-party integrations.


## 0.1.0-dev.8

- Hotfix Supervisor API environment loading under s6-overlay.
- Start the exporter through `/command/with-contenv` so `SUPERVISOR_TOKEN` reaches the Python process.
- No mirror contract, metadata, filtering, or security-policy changes from dev.7.


## 0.1.0-dev.7

- Export all currently installed Home Assistant Apps dynamically under `derived/apps/`.
- Export configured App repositories under `derived/apps/repositories.json`.
- Add Supervisor API access required for App metadata.
- Exclude generic backup/runtime artifacts including Node-RED runtime state.
- Set the project defaults to omit HACS compiled frontend and historical Codex tasks.
- Use a Node-RED folder exclude with explicit includes for flows, settings and package manifests.


## 0.1.0-dev.6

- Distribution-only release to verify native Home Assistant update discovery.
- No exporter behavior or mirror contract changes.

## 0.1.0-dev.5

- Package the exporter as a standard Home Assistant custom App repository.
- Enable normal Home Assistant App update discovery.
- Keep the private target mirror and SSH Deploy Key model unchanged.
- Remove temporary local-development updater tooling.
- Keep scoped Home Assistant/App filters and compact changed-file logging from dev.4.
