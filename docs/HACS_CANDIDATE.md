# Audi Connect 3.0.0b46 — documentation update

Experimental HACS release. V2 remains the default and fallback; V3 is opt-in.

## What's changed

- Clearer installation, configuration, controls, Workbench and diagnostics guides.
- Updated explanations of data freshness, API allowance, trip history and restart behavior.
- Simplified technical documentation and API research, without obsolete build-specific instructions.

Vehicle functionality and entity identities are unchanged from the preceding release.

## Upgrade

Back up Home Assistant, update the existing Audi Connect integration through HACS and restart Home Assistant. Keep the existing configuration entry, devices and entities.

## Known limitations

Vehicle coverage depends on model, market and account permissions. Manufacturer identity may be incomplete, Data Act readings may be delayed, and remote charging or climate actions may not be supported by every vehicle. Verify actual charging power and vehicle behavior independently of Home Assistant command acceptance. Do not automatically replay uncertain commands.

Report issues with your model/year, region, integration and HA versions, expected and actual behavior, and sanitized diagnostics. Never share credentials, VINs or tokens.
