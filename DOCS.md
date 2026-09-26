# HA Config Exporter

Private one-way Home Assistant configuration mirror for ChatGPT audit, diagnostics and guidance.

This App is **not a backup**, **not disaster recovery**, and **not GitOps**. Home Assistant is always the source of truth.

## Export model

Each run:

1. reads the current selected configuration from Home Assistant;
2. rebuilds the managed mirror roots;
3. preserves repository-only files outside those roots;
4. compares the complete resulting Git tree with the current remote snapshot;
5. does nothing when the tree is unchanged;
6. when changed, publishes one new parentless/root commit.

There is intentionally no history chain between exports.

## Source hierarchy

Direct filesystem content keeps the real Home Assistant App mount hierarchy:

- `/homeassistant/...` -> `homeassistant/...`
- `/addon_configs/...` -> `addon_configs/...`

Generated/API-derived data, when added later, belongs under `derived/`.

## Configuration-visible ordinary excludes

Ordinary excludes are defined in the App **Configuration** screen. They are user-editable and may be overridden by an explicit `include`.

The default profile is based on the proven production fj8 exporter and currently excludes:

- Home Assistant databases: `*.db`, `*.db-shm`, `*.db-wal`
- logs: `*.log*`
- compressed/runtime files: `*.gz`
- Python caches: `__pycache__`
- OS/editor noise: `._*`, `.DS_Store`
- dependency/cache trees: `deps/`, `.cache/`
- legacy/runtime paths: `known_devices.yaml`, `tts/`, `.ha_run.lock`
- Zigbee2MQTT runtime data: `coordinator_backup.json`, `state.json`, `device_icons/`
- ML runtime data: `ml_weather/data/`, `ml_weather/output/`, `ml_weather/models/`
- Codex runtime/input data: `codex_input/`
- generated/local media paths: `image/`
- generated frontend/runtime content: `www/codex_cli_auth/`, `www/community/`, `www/calendars/`
- the broad `codex_tasks/` tree, with only `*/task.json` restored by the default include rule
- App dependency/runtime noise: `node_modules/`, `__pycache__/`, `*.backup`

These are ordinary scope rules, not security controls. They are intentionally visible and editable.

## Built-in hard security deny

The following protections are implemented in code and **cannot be overridden by Configuration or include rules**:

- Git metadata: `.git`
- real `secrets.yaml` / `secret.yaml`
- Home Assistant authentication storage: `.storage/auth*`
- `.storage/auth_provider.homeassistant`
- `.storage/core.config_entries`
- `.storage/application_credentials`
- `.storage/cloud`
- Home Assistant `.cloud/`
- Node-RED credential files: `flows_cred*`
- Node-RED user credential config: `.config.users.json*`
- generic credential files: `credentials.json`, `credentials.*`
- private key material: `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`

A final pre-push content scan also blocks high-confidence GitHub tokens and private-key signatures.

## Sanitized configuration retained for audit

Some files are useful for audit but contain secrets. Instead of dropping the entire file, the exporter preserves its useful structure and redacts sensitive values.

Currently:

- `homeassistant/secrets.yaml`: key names are retained, values are blanked;
- `homeassistant/zigbee2mqtt/configuration.yaml`: MQTT password is replaced with `<redacted>`;
- Zigbee2MQTT `advanced.network_key`: replaced with `<redacted>`.

## Home Assistant .storage policy

The exporter does **not** mirror all of `.storage`.

Default useful audit scope includes:

- `core.*registry`
- `lovelace*`
- `zone`

This includes the entity, device, area, floor and label registries while avoiding authentication/runtime storage.

Explicit include rules may add other non-hard-denied `.storage` files later.

## Include / exclude precedence

Evaluation order:

1. hard security deny;
2. default `.storage` scope;
3. Configuration `exclude`;
4. explicit Configuration `include` may restore ordinary excluded/scope paths;
5. hard security deny remains authoritative;
6. sanitizers run;
7. pre-push security scan runs.

## Authentication

The App uses its own persistent Ed25519 SSH Deploy Key for the target mirror repository.

No GitHub PAT is required.

The target repository Deploy Key must have write permission because the exporter replaces the snapshot branch tip.

## Logging

Every exporter run begins and ends with a visible `########################################################################` separator.

Exporter-owned messages contain:

- local ISO timestamp;
- colored severity: `INFO`, `WARN`, `ERROR`, `OK`;
- explicit `RUN START` and `RUN END` status.

Home Assistant/S6 container lifecycle messages are generated outside the exporter and therefore do not use this formatter.
