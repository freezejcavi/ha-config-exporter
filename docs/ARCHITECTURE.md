# Architecture v1

## Goal

Provide ChatGPT a current, truthful, compact analytical view of useful Home Assistant configuration without turning Git into a backup or deployment source.

## Pipeline

1. Read App options from `/data/options.json`.
2. Ensure a persistent repository-scoped SSH Deploy Key exists.
3. Fetch the configured target repository.
4. If the guarded legacy signature `config/configuration.yaml` exists, remove only the known old mirror roots.
5. Preserve repository-only/unmanaged paths.
6. Remove and rebuild managed mirror roots.
7. Mirror selected data from `/homeassistant` and `/addon_configs`.
8. Generate Supervisor App metadata under `derived/apps/`.
9. Generate custom-component provenance under `derived/custom_components/index.json`.
10. Apply sanitization.
11. Run the final content scan.
12. Compare the candidate tree with the current remote tree.
13. If identical, do nothing.
14. If different, create a new parentless/root commit and move the branch tip.

## Managed roots

- `homeassistant/`
- `addon_configs/`
- `derived/`

Everything else is unmanaged repository-only content and is preserved.

## Home Assistant mirror policy

Useful HA YAML/configuration, selected registries, Lovelace storage dashboards/resources, Zigbee2MQTT configuration/custom converters, local analytical code and Codex task records are retained.

Runtime/generated noise is excluded.

Codex task policy:

- broad `codex_tasks/**` exclude
- restore only `codex_tasks/*/task.json`

## Custom-component policy

Full source is retained only for locally developed components:

- `battery_health`
- `anime_benchmark`

Third-party custom integrations use metadata-only export.

The component provenance index records version, source, requirements, export mode and installed-tree SHA-256 so exact upstream code can be reconstructed or compared when needed.

## App metadata

Supervisor API data is exported dynamically to:

- `derived/apps/<slug>.json`
- `derived/apps/repositories.json`

## Node-RED policy

Retain only:

- `flows.json`
- `settings.js`
- `package.json`
- `package-lock.json`

Exclude runtime context/state/generated metadata.

## Security ordering

1. hard deny;
2. built-in ordinary source/storage policy;
3. user exclude;
4. user include exception;
5. sanitizers;
6. final content scan.

## Snapshot semantics

- no history chain between exports
- changed run -> one new parentless/root commit
- unchanged run -> no push
- live Home Assistant/Node-RED remain source of truth

## Production migration behavior

Version 0.1.1 contains a guarded one-time legacy-layout cleanup.

It activates only when `config/configuration.yaml` exists and removes:

- `config/`
- `addons/`
- `lovelace/`
- `node-red/`
- top-level `esphome/`

Repository-only `README.md` and `docs/` are preserved.

## Current production state

Stable release: `0.1.1`

Accepted production mirror: **226 files, 0 symlinks**, followed by an immediate deterministic no-change run.
