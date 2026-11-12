# Audi Connect V3 — community preview

**More capabilities. Less configuration. Built together.**

Building on the original Audi Connect integration, V3 explores a capability-driven approach for Home Assistant: connect once, discover what your particular Audi supports, and use native HA entities. Unsupported or unverified functions should not be presented as guaranteed working features.

We are inviting Audi owners and integration developers to try the **experimental 3.0.0b19** fork prerelease and help validate it across models, model years, regions and API generations.

## What's different

- Automatic reviewed read discovery and capability-aware native entities.
- One account and integration entry, with V2 as default and rollback choice.
- Better vehicle status, trip and freshness evidence where supported.
- Guarded remote commands; no automatic physical actions during discovery.
- Optional admin Engineering Workbench to investigate gaps, test reviewed alternatives with consent and contribute reusable mappings.
- Structural native diagnostics for issue reports, without API response previews or private trip values.

## Try it

Back up Home Assistant. Add [the fork](https://github.com/npinguin/audi_connect_ha) to HACS as a custom Integration repository, select [3.0.0b19](https://github.com/npinguin/audi_connect_ha/releases/tag/3.0.0b19) (show prereleases), restart HA, then choose V3 in Audi Connect runtime options. Keep existing entity IDs and your config entry; use V2 runtime options to roll back. Package rollback is separate.

[Step-by-step guide](V3_COMMUNITY_HOWTO.md) · [Release notes](V3_RELEASE_NOTES_3.0.0b19.md) · [Diagnostics and privacy](V3_COMMUNITY_DIAGNOSTICS.md)

## Help us test

Report your model/year/powertrain, region, HA version, V2/V3 behavior and whether the same function works in myAudi. Attach native integration diagnostics after reviewing them for private information. No VIN, credentials, S-PIN, token, callback URL, raw payloads or private location/trip history. Do not repeat uncertain remote commands.

[Report an issue in the fork](https://github.com/npinguin/audi_connect_ha/issues).

## Status

1,058 Python tests passed on each of HA 2026.7.0 and 2026.11.1, plus Workbench, hassfest, HACS and package checks ([release CI](https://github.com/npinguin/audi_connect_ha/actions/runs/43321338969)). This is software validation, not physical certification across Audi vehicles. Identity recovery, cross-model evidence, full V2 parity and live restart/rollback validation remain open. V3 is not part of the official upstream stable release.

We welcome feedback and would like to agree the upstream review and delivery approach with the original maintainers. No upstream merge is requested at this stage.
