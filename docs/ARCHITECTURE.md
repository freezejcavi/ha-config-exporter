# Architecture v1

## Goal

Provide ChatGPT a current, truthful and sufficiently broad view of useful Home Assistant configuration without turning Git into a backup or deployment source.

## Pipeline

1. Read App options from `/data/options.json`.
2. Ensure a persistent repository-scoped SSH Deploy Key exists.
3. Fetch/clone the current test mirror repository.
4. Preserve repository-only/unmanaged paths.
5. Remove and rebuild only managed mirror roots.
6. Mirror useful text/config data from `/homeassistant` and `/addon_configs`.
7. Apply hard security deny, storage policy, ordinary exclude and explicit include semantics.
8. Create sanitized `homeassistant/secrets.yaml`.
9. Run a pre-push secret scan.
10. Compare the candidate Git tree with the current remote tree.
11. If identical and the remote snapshot is already parentless, do nothing.
12. If different, create a new parentless commit and update the branch with `--force-with-lease`.

## Managed roots

- `homeassistant/`
- `addon_configs/`
- `derived/` (reserved for later API-derived/sanitized views)

Everything outside these roots is unmanaged and preserved.

## Security ordering

1. hard deny;
2. default source/storage scope;
3. user ordinary excludes;
4. explicit includes may restore ordinary exclusions/scope;
5. hard deny remains authoritative;
6. pre-push content scan can block the entire export.

## Deliberate v1 choices

- broad capture first, evidence-based cleanup later;
- no Supervisor API-derived views yet;
- no history between exports;
- no production repository access;
- no PAT authentication;
- no upstream Poeschl workflow/runtime dependency.
