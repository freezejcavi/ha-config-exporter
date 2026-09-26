# Project log — 2026-09-26

## Goal

Build a purpose-built Home Assistant configuration exporter for ChatGPT audit/guidance.

The exporter is not a backup, disaster-recovery mechanism, or GitOps source. Live Home Assistant and Node-RED remain the source of truth.

## Final release state

- stable App: `0.1.1`
- source: `freezejcavi/ha-config-exporter`
- production mirror: `freezejcavi/home-assistant-config`
- production App slug: `e3fcb3fb_ha_config_exporter`
- latest accepted production snapshot: `6ea85ad5`
- prepared mirror: **226 files, 0 symlinks**
- second validation run: **SUCCESS / NO CHANGE**
- distribution: native Home Assistant custom App repository
- authentication: persistent repository-scoped SSH Deploy Key
- publishing: one parentless/root commit per changed snapshot

## Final architecture

### Source hierarchy

- `/homeassistant/... -> homeassistant/...`
- `/addon_configs/... -> addon_configs/...`
- Supervisor/API-derived content -> `derived/...`

Repository-only files outside managed roots are preserved.

### Snapshot model

Every changed run publishes a fresh parentless/root commit.

If the resulting tree is identical, nothing is pushed.

### Filtering

Filtering layers:

1. hard security deny;
2. built-in ordinary exclusions;
3. user exclude;
4. user include exception;
5. sanitizers;
6. final content scan.

Built-in HA noise exclusions include databases, logs, caches, `node_modules`, backup files, Zigbee2MQTT runtime state, weather-model data/output/model artifacts, auth/codex input/runtime folders, and broad Codex task contents.

Only `codex_tasks/*/task.json` is restored for later analysis.

### Custom integrations

Locally developed integrations remain full-source:

- `battery_health`
- `anime_benchmark`

Third-party custom integrations are metadata-only. The mirror retains canonical metadata such as manifests, strings/icons, YAML descriptors and EN/CS translations.

`derived/custom_components/index.json` records:

- domain/name
- version
- upstream source
- requirements
- export mode
- installed-tree SHA-256
- nested integration/link information

This keeps the mirror lean while preserving exact provenance for upstream reconstruction.

### Home Assistant Apps

Installed Apps are discovered dynamically through the Supervisor API and exported under:

- `derived/apps/<slug>.json`
- `derived/apps/repositories.json`

No hard-coded App list is used.

### Node-RED

The final allowlist retains only:

- `flows.json`
- `settings.js`
- `package.json`
- `package-lock.json`

Runtime context, websocket state, generated registries and backups are excluded.

## Release history completed today

- dev.5: native App repository packaging
- dev.6: update-discovery verification
- dev.7: Supervisor/App metadata and runtime-noise cleanup
- dev.8: s6 `with-contenv` fix for `SUPERVISOR_TOKEN`
- dev.9: lean analytical mirror + component provenance + restored Codex task records
- 0.1.0: first stable release with explicit mirror target
- 0.1.1: guarded cleanup of legacy production mirror roots

## Production cutover

The new exporter was pointed at `freezejcavi/home-assistant-config` and successfully published the new analytical layout.

The first 0.1.1 run removed 2233 legacy-path changes and produced snapshot `6ea85ad5`.

A second immediate run returned no change, proving deterministic output.

Legacy roots removed:

- `config/`
- `addons/`
- `lovelace/`
- `node-red/`
- top-level `esphome/`

Repository-only documentation under `docs/` and the root README were preserved.

The previous exporter flow was disabled, and the legacy `5daec847_git-exporter` no longer appears in Supervisor inventory.

## Final status

**Project complete. No release blockers remain.**

Future work should be evidence-driven maintenance only.
