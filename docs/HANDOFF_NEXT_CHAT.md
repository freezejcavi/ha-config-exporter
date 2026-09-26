# Next-chat handoff — HA Config Exporter

Continue the project **Home Assistant Config Exporter**, currently at **0.1.0-dev.6**, stabilization before stable `0.1.0`.

## Current verified state

The exporter is now a normal Home Assistant custom App repository:

- source: `freezejcavi/ha-config-exporter`
- App version: `0.1.0-dev.6`
- normal HA System/Updates flow verified with dev.5 -> dev.6
- target during development: private `freezejcavi/home-assistant-config-v2-test`
- latest successful dev.6 snapshot: `1a884cb37bd01267af3ffca7fbffc32454a2c429`
- that snapshot has **0 parents**
- live HA/Node-RED remains source of truth
- mirror is audit/guidance only, never backup or GitOps

Do not redesign the distribution/update mechanism again; it is solved.

## Architecture contract

Managed roots:

- `homeassistant/`
- `addon_configs/`
- `derived/` reserved for sanitized API-derived data

Changed snapshots are parentless/root commits. No-change runs publish nothing.

Security:

- hard-deny sensitive auth/private-key paths
- sanitized `secrets.yaml`
- sanitized Zigbee2MQTT password/network key
- final pre-push secret scan
- SSH write Deploy Key scoped to target mirror

## Most recent parity result

A direct old-vs-dev.6 mirror comparison found:

- old production mirror: 2234 files
- dev.6 test mirror: 2188 files
- 57 old-only after mapping `config/...` -> `homeassistant/...`

Only **11 are a meaningful missing information layer**: old Supervisor/App API exports:

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

Do **not** recreate `addons/`. Implement equivalent sanitized Supervisor-derived metadata under:

```text
derived/apps/
```

The remaining old-only files are intentional:
- 31 binary/static assets with no audit value
- 13 duplicate representations already captured at truthful source paths
- 2 historical repo-only docs that will be preserved at production cutover

No `addon_configs` parity gap exists.

## Immediate next task

Start with **Supervisor/App metadata parity**.

Requirements:

- use Supervisor API, not filesystem guessing;
- capture installed App configuration/status information useful for ChatGPT audit;
- capture configured App repositories;
- write sanitized deterministic output under `derived/apps/`;
- never export passwords, tokens, auth material or private keys;
- add unit tests;
- preserve parentless snapshot behavior;
- no unrelated feature additions.

Before implementing, inspect what the old exporter emitted in the production mirror and identify which fields are actually useful versus sensitive/noisy.

## Remaining blockers after that

### Runtime noise

Exclude:

```text
a0d7b954_nodered/context/**
```

from built-in `addon_configs` filtering.

Reason: `context/global/global.json` contains live values/timestamps and causes meaningless snapshot churn.

Then run twice with no config change. Second run must say:

```text
No changes detected — nothing pushed.
```

### Node-RED trigger migration

The live mirrored flow still starts:

```text
app: 5daec847_git-exporter
```

and checks:

```text
binary_sensor.home_assistant_git_exporter_node_red_fix_bezi
```

The new App Supervisor slug is `e3fcb3fb_ha_config_exporter`.

Keep the existing event-driven trigger model; only repoint it after the new exporter is ready. Do not redesign the flow unless evidence requires it.

### Stable defaults

The public App currently defaults to:

```text
git@github.com:freezejcavi/home-assistant-config-v2-test.git
```

That must not remain as the stable public default. Make stable configuration require the user's own target repository instead of silently targeting the developer test repo.

### Production cutover

Only after the above:

1. stop/disable the old exporter writer;
2. configure new exporter target to `freezejcavi/home-assistant-config`;
3. add new production write Deploy Key;
4. smoke run;
5. verify parentless commit, security/sanitization, repository-only content preservation and delta;
6. repoint Node-RED to the new App;
7. retire old exporter after observation.

## Guardrails

No new feature work without a real release reason.

Do not:
- build another updater;
- change Git to source of truth;
- add restore/deploy behavior;
- optimize broad capture prematurely;
- remove useful files just to reduce repository size;
- change old `freezejcavi/git-exporter` while it remains rollback protection.
