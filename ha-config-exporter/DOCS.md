# HA Config Exporter

One-way Home Assistant configuration mirror for ChatGPT audit, diagnostics and guidance.

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

## Filtering model

Filtering is deliberately split into three layers.

### 1. Built-in base policy

Known installation/runtime noise is excluded by the App itself. These rules are part of the product policy and therefore do not fill the Configuration screen with dozens of default chips.

For `/homeassistant`, the built-in base policy excludes:

- `*.db`, `*.db-shm`, `*.db-wal`
- `*.log*`, `*.gz`
- `**/__pycache__/**`, `**/._*`, `**/.DS_Store`
- `**/deps/**`
- `known_devices.yaml`, `tts/**`, `.cache/**`, `.ha_run.lock`
- `zigbee2mqtt/coordinator_backup.json`, `zigbee2mqtt/state.json`, `zigbee2mqtt/device_icons/**`
- `ml_weather/data/**`, `ml_weather/output/**`, `ml_weather/models/**`
- `codex_input/**`, `image/**`
- `www/codex_cli_auth/**`, `www/community/**`, `www/calendars/**`
- the broad `codex_tasks/**` tree

The built-in exception to that last rule restores:

- `codex_tasks/*/task.json`

For `/addon_configs`, the built-in base policy excludes:

- `**/__pycache__/**`
- `**/node_modules/**`
- `**/*.backup`

### 2. User exclude

The Configuration screen starts with empty user filters.

There are separate scopes:

- **homeassistant** — paths are relative to `/homeassistant`
- **addon_configs** — paths are relative to `/addon_configs`

Examples:

- `codex_input/**`
- `zigbee2mqtt/device_icons/**`
- `a0d7b954_nodered/cronplusdata/**`

Do not repeat `/homeassistant/` or `/addon_configs/` in the UI.

A user exclude can remove something that the built-in base policy would normally keep.

### 3. User include

User include is an exception mechanism, not a positive allow-list.

Typical use:

- exclude `some_folder/**`
- include `some_folder/important.json`

A user include may restore content excluded by the built-in ordinary policy, the default `.storage` scope, or a user exclude.

It can never restore a hard security deny.

## Built-in hard security deny

The following protections are implemented in code and **cannot be overridden** by Configuration or include rules:

- Git metadata: `.git`
- real `secrets.yaml` / `secret.yaml`
- Home Assistant authentication storage: `.storage/auth*`
- `.storage/auth_provider.homeassistant`
- `.storage/core.config_entries`
- `.storage/application_credentials`
- `.storage/cloud`
- Home Assistant `.cloud/**`
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

A user include may restore another safe `.storage` file when needed; hard-denied storage can never be restored.

## Effective precedence

For each file:

1. hard security deny;
2. built-in base policy and built-in exception;
3. user exclude;
4. user include;
5. sanitizers;
6. final pre-push security scan.

This gives the intended `exclude folder -> include selected file` behavior without making include an allow-list.

## Authentication

The App uses its own persistent Ed25519 SSH Deploy Key for the target mirror repository.

No GitHub PAT is required.

The target repository Deploy Key must have write permission because the exporter replaces the snapshot branch tip.

## Logging

Every exporter run begins and ends with a visible `########################################################################` separator.

The normal user-facing log is intentionally concise. It shows:

- timestamped, colored `INFO`, `WARN`, `ERROR`, and `OK` messages;
- the size of the prepared mirror;
- the **actual Git delta** as `A` (added), `M` (modified), or `D` (deleted) file paths;
- at most 30 changed paths per run, followed by a count of remaining paths;
- an explicit no-change result when nothing needs to be pushed;
- a short snapshot SHA after a successful publish;
- explicit `RUN START` and `RUN END` status.

Low-value internal Git details such as full tree SHA, remote SHA and the raw result JSON are deliberately not printed during a normal run.

Home Assistant/S6 container lifecycle messages are generated outside the exporter and therefore do not use this formatter.
