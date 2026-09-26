# HA Config Exporter Updater

Private helper App for keeping the local **HA Config Exporter** App synchronized with its private GitHub source repository.

## Why this helper exists

HA Config Exporter is intentionally installed as a **local App** from `/addons/ha-config-exporter`.

Home Assistant's Local Apps repository detects local file changes, but it does not authenticate to and pull the private source repository for us. Giving the exporter itself write access to `/addons` and manager access to Supervisor would unnecessarily widen its privileges.

This helper keeps those privileges isolated.

## What one run does

1. Uses its own persistent read-only SSH Deploy Key.
2. Checks `freezejcavi/ha-config-exporter:main`.
3. Refuses to continue if the local source checkout contains manual modifications.
4. Fast-forwards `/addons/ha-config-exporter` only when GitHub changed.
5. Reloads the Supervisor App store.
6. If the exporter version changed, asks Supervisor to update the local exporter App.
7. Exits.

No change means no rebuild.

## First run

The first run generates a public SSH key and prints it in the log.

Add that key to:

`freezejcavi/ha-config-exporter -> Settings -> Deploy keys`

Do **not** enable write access.

Run the updater again afterwards.

## Intended automation

The updater is a one-shot App. It should be started before HA Config Exporter.

Recommended Node-RED sequence:

`Start updater -> wait until updater stops -> Start exporter`

This guarantees that each export uses the latest released exporter version without keeping either App permanently running.

## Security

The updater has elevated privileges because it must:

- write to the local `/addons` tree;
- call Supervisor's App update API.

The exporter itself keeps its narrower read-only permissions.

The source Deploy Key is read-only and is persisted only in the updater's private `/data/ssh`.
