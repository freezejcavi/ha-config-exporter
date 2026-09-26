# HA Config Exporter

Home Assistant App for a one-way configuration mirror used by ChatGPT for audit, diagnostics and guidance.

## Product contract

This project is **not a backup** and is **not GitOps**.

- source of truth: live Home Assistant
- direction: Home Assistant -> GitHub only
- destination: one complete current snapshot
- publish: only when the resulting Git tree changes
- history: each published snapshot is a parentless/root commit
- Git content is never applied back to Home Assistant

## Home Assistant installation

Add this repository to the Home Assistant App Store:

`https://github.com/freezejcavi/ha-config-exporter`

Then install **HA Config Exporter** from the repository.

Future App versions are delivered through the normal Home Assistant update mechanism.

## Development target

The current development target remains isolated:

`git@github.com:freezejcavi/home-assistant-config-v2-test.git`

The production `home-assistant-config` repository is not touched until cutover is explicitly approved.

## Authentication to the private mirror

The App uses a dedicated SSH Deploy Key scoped to the target mirror repository. No GitHub PAT is stored in App options.

On first run the App creates an Ed25519 key under persistent `/data` and prints the public key. Add that key to the target mirror repository with **Allow write access** enabled, then run the App again.

## Source hierarchy

Direct filesystem data keeps the real Home Assistant App mount path:

- `/homeassistant/...` -> `homeassistant/...`
- `/addon_configs/...` -> `addon_configs/...`

Selected `.storage` audit data is enabled by default. Built-in ordinary filtering is documented in the App documentation; user include/exclude options are root-relative overrides.

## Current phase

**0.1.0-dev.6** — distribution-only update discovery validation on the native Home Assistant App repository.
