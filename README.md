# HA Config Exporter

Private Home Assistant App for a one-way configuration mirror used by ChatGPT for audit, diagnostics and guidance.

## Product contract

This project is **not a backup** and is **not GitOps**.

- source of truth: live Home Assistant
- direction: Home Assistant -> GitHub only
- destination: one complete current snapshot
- publish: only when the resulting Git tree changes
- history: each published snapshot is a parentless/root commit
- Git content is never applied back to Home Assistant

## v0.1 development target

The development target is intentionally isolated:

`git@github.com:freezejcavi/home-assistant-config-v2-test.git`

The production `home-assistant-config` repository is not touched during development.

## Source hierarchy

Direct filesystem data keeps its real Home Assistant App mount path:

- `/homeassistant/...` -> `homeassistant/...`
- `/addon_configs/...` -> `addon_configs/...`

Repository-only paths such as `README.md` and `docs/` are preserved.

The initial selector is intentionally broad. Ordinary `exclude` rules can be overridden with explicit `include` rules, while hard security denies cannot.

Selected `.storage` audit data is enabled by default, including `core.*registry`, Lovelace storage and zones.

## Authentication

The App uses a dedicated SSH Deploy Key scoped to the target mirror repository. No GitHub PAT is stored in App options.

On first run the App creates an Ed25519 key under persistent `/data` and prints the public key. Add that key to the target repository:

**Settings -> Deploy keys -> Add deploy key -> Allow write access**

Then run the App again.

GitHub SSH host keys are obtained from GitHub's HTTPS metadata endpoint and stored in the App's persistent data before SSH is used.

## Local Home Assistant installation

This is a private/local App.

Clone or copy this repository into:

`/addons/ha-config-exporter`

so that:

`/addons/ha-config-exporter/config.yaml`

exists.

Then reload the Local Apps store and install **HA Config Exporter**.

The App uses the modern Home Assistant mounts:

- `homeassistant_config` read-only -> `/homeassistant`
- `all_addon_configs` read-only -> `/addon_configs`

## Safety

Hard-denied content includes authentication databases, `core.config_entries`, application credentials, private keys, real secrets files and Node-RED credential flows.

A second pre-push scan blocks high-confidence token/private-key signatures and non-redacted sensitive values in configuration-like files.

## Current phase

**0.1.0-dev** — build the isolated v2 test mirror, inspect it, then refine ordinary excludes from evidence before any production cutover.
