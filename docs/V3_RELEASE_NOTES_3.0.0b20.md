# Audi Connect 3.0.0b20 — upstream review test

Experimental HACS prerelease for testing the exact runtime of [upstream PR #918](https://github.com/audiconnect/audi_connect_ha/pull/918) at commit `14f2b2ba8a8cfc538998be435d4b9449160cabc6`.

- Runtime content matches the upstream review snapshot, except for the manifest version.
- Upstream V2 read-only probe service is retained. V3 uses its own read discovery.
- V2 remains default and fallback; V3 is opt-in.
- Minimum tested Home Assistant version: 2026.7.0.
- This is not a stable release or upstream acceptance.

See [issue validation matrix](https://github.com/npinguin/audi_connect_ha/blob/release/upstream-v3-b20/docs/V3_COMMUNITY_ISSUE_MATRIX.md) for targeted community tests.

Back up Home Assistant, select the explicit prerelease in HACS, restart, and validate existing V2/V3 entities, trip data, vehicle identity, controls and restart/rollback. Never repeat uncertain vehicle commands. Share only reviewed integration-specific diagnostics, not the full HA download.
