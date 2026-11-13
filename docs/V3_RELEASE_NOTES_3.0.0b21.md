# Audi Connect 3.0.0b21 — last-known telemetry

Experimental HACS prerelease based on upstream review PR #918 plus the targeted last-known telemetry correction.

- Preserve valid last-reported door, window, plug and selected charging states while the car sleeps.
- Expose the original vehicle capture and age, not a renewed cloud receipt.
- Advance vehicle age and freshness on the local HA clock, without extra API calls.
- Retain individual readings omitted in partial access responses. Explicit unknown or contradictory components and incomplete aggregates are not treated as safe.
- Keep instantaneous power, active command confirmation, and command readback freshness gates.
- Retain same-VIN telemetry during compatible manufacturer identity refinement; invalidate control applicability separately.
- Preserve existing entity identities and V2 fallback.

This change does not introduce a new cache service or guarantee generic persistent telemetry across a full restart. Backup before testing. Check the current vehicle capture and freshness before relying on any displayed access or charging state in automations. Never infer current physical safety from an old reading.

Validation: HA 2026.7.0 and 2026.11.1, Workbench, pre-commit, HACS, hassfest and runtime equivalence. No stable promotion or upstream acceptance is implied.

Source: [telemetry correction branch](https://github.com/npinguin/audi_connect_ha/tree/fix/v3-last-known-telemetry) and [upstream PR #918](https://github.com/audiconnect/audi_connect_ha/pull/918).
