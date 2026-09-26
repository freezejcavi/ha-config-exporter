# Next-chat handoff — HA Config Exporter

Project status: **CLOSED / production stable**.

## Current production state

- source repository: `freezejcavi/ha-config-exporter`
- current App version: `0.1.1`
- production mirror: `freezejcavi/home-assistant-config`
- production exporter App slug: `e3fcb3fb_ha_config_exporter`
- legacy exporter flow is disabled
- legacy exporter App is no longer present in Supervisor inventory
- latest accepted production run: `6ea85ad5`
- prepared mirror: **226 files, 0 symlinks**
- immediate second run: **SUCCESS / NO CHANGE**
- snapshot model: parentless/root-only, no history chain

Home Assistant and Node-RED remain the source of truth. The GitHub mirror is analytical only, not backup, DR, or GitOps.

## Final mirror contract

Managed analytical roots:

- `homeassistant/`
- `addon_configs/`
- `derived/`

Repository-only documentation outside these roots is preserved.

### Home Assistant

Retains useful YAML/configuration, selected `.storage` registries/Lovelace data, Zigbee2MQTT configuration/custom converters, Codex task records, and local analytical code.

`codex_tasks/**` is excluded broadly, with the built-in exception:

`codex_tasks/*/task.json`

### Custom integrations

- full source: `battery_health`, `anime_benchmark`
- third-party integrations: metadata-only analytical mirror
- component provenance: `derived/custom_components/index.json`
- index records version, upstream source, requirements, export mode and installed-tree SHA-256

### Apps

Supervisor metadata is discovered dynamically every run:

- `derived/apps/<slug>.json`
- `derived/apps/repositories.json`

### Node-RED

Only these files are retained:

- `flows.json`
- `settings.js`
- `package.json`
- `package-lock.json`

Runtime context/state files are excluded.

## Production acceptance

Production cutover was completed on 2026-09-26.

The first 0.1.1 migration run removed the legacy mirror roots:

- `config/`
- `addons/`
- `lovelace/`
- `node-red/`
- top-level `esphome/`

while preserving repository-only `README.md` and `docs/`.

The second run immediately returned:

`No changes detected — nothing pushed.`

The one-file reduction from 227 to 226 was explained by removal of the legacy `5daec847_git-exporter` from Supervisor inventory.

## Future work

No open release blockers remain.

Any future change should start from a concrete analytical need or regression. Do not redesign distribution, snapshot semantics, or filtering without evidence.
