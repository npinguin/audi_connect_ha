# Audi Connect 2.5.3b10 — field test follow-up

This prerelease incorporates feedback from a real vehicle test on November 10, 2026.

## Confirmed in the field (previous test candidate)

- Door lock and unlock: physical operation confirmed.
- Flash lights: physical operation confirmed.
- Native **Climatisation ON/OFF** switch: physical on and off confirmed.

## Changes in this candidate

- Remove the two newly introduced, now redundant Home Assistant buttons **Start climate (car settings)** and **Stop climate**. The native stateful switch supersedes them.
- Keep the shared underlying start/stop API functions and the stable native climate switch; no change to its unique ID.
- Add a regression test so the duplicate buttons are not accidentally reintroduced.

## Known limitations (not fixed or claimed working)

- **Preheater:** not working on the tested vehicle; already non-functional before the fork changes.
- **Original Climatisation climate entity:** action does not work on the tested vehicle, although the separate native ON/OFF switch works. This legacy entity remains for upstream compatibility.
- **Charge mode:** requests are transmitted but rejected by Audi. This is not proof of a successful mode change.
- Other experimental remote commands remain opt-in and require separate physical acceptance.
- Some read-only sensors remain unavailable when the Audi backend does not return the expected values.

## Local verification

1. Back up Home Assistant; do not delete or recreate the Audi Connect config entry.
2. Install the GitHub prerelease `v2.5.3b10` via HACS after validation and publication; restart HA.
3. Confirm the native climate ON/OFF switch still works, and lock/unlock and flash still work.
4. Confirm the two obsolete button entities are not newly created. If Home Assistant retains an orphaned registry record, remove it manually after confirming no automations use it.
5. Record whether the original climate entity, preheater, and charge-mode behavior remains unchanged.
6. Do not submit upstream until CI and this vehicle regression test pass.

The actual working capability may differ by model, region, Audi backend, and account permission. A successful HTTP response is not physical success.
