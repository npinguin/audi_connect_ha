# Audi Connect 3.0.0b52 — final V3 refinement

Experimental HACS TEST prerelease for live acceptance. V2 remains the default and fallback; V3 is opt-in. This is not a stable release.

## What's changed

- Routine V3 configuration changes now save without automatically opening vehicle discovery. Select Vehicle setup & discovery explicitly to review or retest individual vehicle functions.
- Existing guided and selective discovery, configuration, entity identities, history and V2 rollback remain available. No changes to charging command dispatch or the default-off STOP recovery policy.
- Added regression coverage for changes to recovery consent during an in-flight STOP request, including enabling recovery after the original intent and disabling it before scheduling.
- Automated qualification uses Home Assistant 2026.11.2. The existing B51 charging STOP recovery and B50 telemetry, Data Act and optional parking address improvements remain included.

## Upgrade and test

Back up Home Assistant, update the existing integration via HACS and restart. Keep existing entries, devices and entities. Confirm that routine Options changes save normally; use Vehicle setup & discovery when you want to test a function. Verify physical remote actions against the vehicle or charger, not the HTTP result alone.

## Known limitations

Physical STOP reliability remains unproven. Vehicle support varies; OEM data can be delayed or unavailable. No stable promotion or upstream acceptance is claimed. Share only sanitized diagnostic evidence; do not share credentials, VINs, tokens, raw responses or private locations.
