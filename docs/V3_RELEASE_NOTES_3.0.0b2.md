# Audi Connect 3.0.0b2 — Independent V3 Climate + API Development

**Experimental HACS prerelease. Back up HA before installation.**

This release replaces the original V3 climate shim, which still used the
V2 polling engine, with a genuinely independent V3 vertical slice.

- One existing Audi config entry and OAuth token source; no second login.
- New V3-owned GraphQL vehicle discovery, CARIAD HTTP transport, single
  polling coordinator, request budget and per-vehicle state model.
- Minimal active HA device surface: one Climate, Cloud Last Poll, Vehicle
  Data Age, Climate Capability, V3 Cloud Polling and Cloud Refresh button.
- Old V2 entities are **reversibly disabled, never deleted** while V3 is
  active; switching back to V2 restores only those disabled by migration.
- Administrator-only **Audi V3 Development** sidebar dashboard for
  per-vehicle GET/POST route alternatives, new custom relative API paths,
  typed parameters and JSON payloads, test history and verified selection.
- GET routes may be automatically discovered with schema + capture timestamp
  evidence. No proactive wake.
- Climate Start/Stop variants require explicit user-initiated tests and
  human confirmation. Gateway acceptance is not physical success; an
  unresolved action is not retried. Unsupported controls may be disabled.
- Local HA Store persists route tests and verified choices across restart.
- V3 diagnostics have their own owner and expose sanitized polling and
  capability observations without raw cloud payloads.

**Not yet migrated to V3:** charging, access/lock, vehicle health/mileage,
trips/consumption, legacy MBB and other historic functions. These remain
in the V2 runtime, available through a simple Options rollback.

**Known experimental restriction:** CARIAD stored-settings climate start
is not yet safely ported to V3 and is not silently mapped to bodyless start.
Users may add carefully reviewed experimental request templates. No
automatic sequential physical command testing is shipped yet.

Read [Why / What / How](V3_ARCHITECTURE.md),
[configuration and rollback](V3_CONFIGURATION.md),
and the [test matrix](V3_TEST_MATRIX.md).

**CI/HACS success only certifies the package, not the real Audi Q8.**
Test cloud login, state freshness, single climate entity, action readback,
and V2 rollback before relying on the beta for daily operation.
