# Project log — 2026-09-26

## Goal

Build a purpose-built Home Assistant configuration exporter for ChatGPT audit/guidance.

The exporter is not a backup, disaster-recovery mechanism, or GitOps source. Live Home Assistant and Node-RED remain the source of truth. Git contains only a current selected mirror for inspection.

## Current release state

- App version: `0.1.0-dev.6`
- Source repository: `freezejcavi/ha-config-exporter`
- Distribution: standard Home Assistant custom App repository
- Source repository visibility: public
- Test mirror: `freezejcavi/home-assistant-config-v2-test` (private)
- Production mirror: `freezejcavi/home-assistant-config` (private, still owned by the old exporter workflow)
- Native Home Assistant update discovery: verified end-to-end with dev.5 -> dev.6
- Latest successful dev.6 test snapshot: `1a884cb37bd01267af3ffca7fbffc32454a2c429`
- Snapshot parent count: 0
- Snapshot model therefore remains parentless/root-only as designed

## Completed architecture

### Source hierarchy

Direct filesystem data keeps its truthful source hierarchy:

- `/homeassistant/...` -> `homeassistant/...`
- `/addon_configs/...` -> `addon_configs/...`
- API-derived/synthetic content is reserved for `derived/...`

Repository-only content outside managed roots is preserved.

### Snapshot publishing

Each changed export creates a fresh parentless/root commit. No Git history chain is kept.

No-change runs do not publish.

### Authentication

The exporter uses a dedicated persistent Ed25519 SSH Deploy Key scoped to the target mirror repository with write permission.

No GitHub PAT is stored in App options.

### Filtering

Filtering has three layers:

1. hard security deny;
2. built-in ordinary base exclusions;
3. user exclude/include overrides for safe content.

User include is an exception mechanism, not an allow-list.

### Sanitization

- `homeassistant/secrets.yaml`: key names retained, values blank
- Zigbee2MQTT `mqtt.password`: `<redacted>`
- Zigbee2MQTT `advanced.network_key`: `<redacted>`

### Security verification

Current dev.6 mirror was checked for:

- hard-denied credential/private-key paths
- GitHub PAT/token signatures
- OpenSSH/RSA private-key signatures
- raw `access_token` / `refresh_token` search hits

No blocking leak was found.

### Logging

Normal logs show:

- mirror file/symlink count
- actual Git delta with A/M/D paths
- no-change result
- published short SHA
- explicit RUN START / RUN END

## Native Home Assistant distribution migration

The original local-App development model was removed.

The repository now uses standard Home Assistant custom App repository layout:

```text
repository.yaml
ha-config-exporter/
  config.yaml
  Dockerfile
  DOCS.md
  CHANGELOG.md
  app/
  translations/
```

The temporary standalone updater App and local update helper were removed.

The native repository update path was verified:

`0.1.0-dev.5 -> 0.1.0-dev.6`

Home Assistant discovered and installed the update through the normal System/Updates mechanism. The exporter then ran successfully after update.

## A/B content parity audit

Compared:

- old production mirror: `freezejcavi/home-assistant-config`
- new dev.6 test mirror: `freezejcavi/home-assistant-config-v2-test`

Path normalization used:

- old `config/...` == new `homeassistant/...`

Counts:

- old mirror files: 2234
- dev.6 mirror files: 2188
- old-only after path normalization: 57
- new-only: 11

### Meaningful missing layer: Supervisor/App metadata

11 old-export files are not represented by dev.6:

```text
addons/45df7312_zigbee2mqtt_edge.yaml
addons/5daec847_git-exporter.yaml
addons/8a8d906b_codex_cli_worker.yaml
addons/a0d7b954_glances.yaml
addons/a0d7b954_nodered.yaml
addons/a0d7b954_ssh.yaml
addons/a0d7b954_vscode.yaml
addons/core_configurator.yaml
addons/core_mosquitto.yaml
addons/e3fcb3fb_ha_config_exporter.yaml
addons/repositories.yaml
```

These came from Supervisor/API-derived data in the old exporter and are not supplied by `all_addon_configs`.

Decision: restore this information in the new architecture under `derived/apps/...`, with explicit sanitization. Do not recreate the misleading old top-level `addons/` model.

### Old-only files intentionally not restored

31 files are low-value binary/static assets:

- custom-component branding PNG files
- HACS Roboto WOFF2 fonts
- LibreSpeed binary
- two `www/sounds/*.mp3` files

They have no meaningful ChatGPT audit value.

13 old-only files are duplicate representations already present in dev.6 at their truthful source path:

- Lovelace YAML exports -> `homeassistant/.storage/lovelace*`
- Node-RED `flows.json` / `settings.js` -> `addon_configs/a0d7b954_nodered/`
- ESPHome `.gitignore` -> `homeassistant/esphome/.gitignore`

2 old-only files are repository-only historical documentation:

- `docs/node-red-modernization/README.md`
- `docs/node-red-modernization/TRACKING_LOG.md`

These are not part of source capture and will be preserved when the new exporter eventually targets the production repository.

### Add-on configuration parity

There are no old add-on configuration files missing from dev.6.

The dev.6 mirror actually captures a broader truthful `addon_configs/a0d7b954_nodered/` set than the old exporter.

## Confirmed runtime-noise finding

`addon_configs/a0d7b954_nodered/context/global/global.json` is live runtime state, not configuration.

Between two recent snapshots it changed values such as:

- `lastKnown.temperature.*.state`
- `lastKnown.temperature.*.value`
- `lastKnown.temperature.*.last_live_at`

Decision: exclude at least:

```text
a0d7b954_nodered/context/**
```

from the built-in `addon_configs` base policy before stable.

After this change, run two exports without intentional configuration changes; the second must produce:

```text
No changes detected — nothing pushed.
```

## Existing Node-RED automation still points to old exporter

Current mirrored Node-RED flow `Github automate export pro ChatGPT` still targets the legacy App:

```text
hassio.app_start
app: 5daec847_git-exporter
```

and checks:

```text
binary_sensor.home_assistant_git_exporter_node_red_fix_bezi
```

Current triggers include:

- every 20 minutes
- HA restart path
- successful backup
- Codex done
- Node-RED deploy/start path

The new native exporter is visible in Supervisor metadata as `e3fcb3fb_ha_config_exporter`.

Decision: do not modify Node-RED until the exporter itself is ready. Then replace the old App start/status references with the new exporter.

## Stable 0.1.0 blockers

Only real release/cutover work remains:

1. Add sanitized Supervisor/App repository metadata under `derived/apps/`.
2. Exclude Node-RED runtime context noise and prove a clean no-change run.
3. Repoint the existing Node-RED export automation from the legacy exporter to the new exporter.
4. Remove the hard-coded test mirror URL from the public App's stable default configuration; stable defaults must not point at the developer's private test repository.
5. Perform production cutover:
   - ensure only one writer;
   - point the new exporter at `freezejcavi/home-assistant-config`;
   - provision its production write Deploy Key;
   - run one production smoke export;
   - verify parentless snapshot, sanitization, repository-only preservation and expected delta;
   - only then retire the old exporter workflow.

No new feature work should be added before stable unless it is required by one of these blockers.

## Explicit non-goals before stable

Do not:

- optimize `custom_components` size just because it is large;
- add backup/restore logic;
- add Git -> HA deployment;
- add another updater;
- reintroduce duplicate Lovelace/Node-RED export structures;
- broaden `.storage` without a concrete audit need;
- change snapshot-only/root-commit behavior.
