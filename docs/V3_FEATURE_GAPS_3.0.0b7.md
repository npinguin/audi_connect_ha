# V3 migration gap register — 3.0.0b7 (2026-11-11)

All counts describe **source inventory**, not live working functions on a Q8.
V3 should preserve global historical support while activating only verified
features on the current vehicle.

## Source coverage

- **110 raw V2 attribute references**, **53** with an explicit historical
  CARIAD response path and **57** without one. Aliases and duplicate entity
  keys mean these are *not* 110 distinct HA sensors.
- **22 historical control references** in V2 source; **14 POST operations**
  in the independent V3 catalog are alternative routes, not a declaration
  that all 22 controls are working.
- **72 distinct historical sensor metadata contracts** captured; 25 with
  a V2-defined unit, 21 with a V2 device class. Unitless text/status sensors
  must remain unitless; two dynamic V2 units need proof from live API replies.
- Live, per-car working and failed totals must come from b7 diagnostics,
  never inferred from global catalog counts.

## P0 — necessary for critical-control acceptance

| Feature | Code status | Remaining gap / acceptance criterion |
|---|---|---|
| Climate Start | CARIAD bodyless POST variant + guided test | Real Q8 command, Audi request-ID async status, physical start/readback |
| Climate Stop | CARIAD bodyless POST + guided test | Real Q8 command, async request-ID success/readback and cooldown |
| Wake vehicle | CARIAD empty JSON POST + guided test | Real vehicle test; avoid blind retry and distinguish sleeping vs unavailable |
| Lock / Unlock | CARIAD templates with restricted {SPIN}, guarded tests, HA lock entity | Validate S-PIN semantics, request-ID completion, actual lock state readback and entity availability |
| HA control parity | Button/switch/lock created after verified route | Verify same unique IDs/automation compatibility after V2→V3→V2 reload |

## P1 — read-only data and lifecycle

| Area | Remaining issue |
|---|---|
| CARIAD read-only | Historic mappings without confirmed V3 paths and per-model results; 2xx/missing mapping/freshness distinguished |
| Legacy MBB | Only charger/climater source mappings are piloted; region/auth differences, more GET/POST services and control responses incomplete |
| Derived sensors | Missing V2 computations, status transformations, indicator interpretations and proper binary semantics for every field |
| Unit normalization | Known V2 metadata restored; source units/conversion must be configured per verified API path, not inferred by HA entities |
| Dynamic unit fields | `actual_charge_rate`, `remaining_charging_time` await confirmed route-unit declarations; never assume A/min |
| Entity platforms | V3 has climate, sensor, binary sensor, button, switch, lock; V2 number/select and several capability-specific controls not yet reintroduced |
| Polling | Complete per-capability refresh, change-triggered readback, partial errors, rate-limits and API quota reconciliation |
| Request-ID lifecycle | Track accepted vs processed/rejected vs completed; GET readback confirmation for controls |
| Legacy/multi-vehicle | Live tests on multiple models, auth families, regions and VIN exclusion behavior |

## P2 — supported historical functionality backlog

- Charging targets, charge mode, per-location targets, timers and profiles
- Remote lights/flash, auxiliary heating/preheater and engine start/stop
- Service data/maintenance indicators, vehicle access details, trip statistics
- Mobility/parking location (privacy-sensitive, explicit opt-in only)
- Vehicle-specific device availability, source timestamps and stale-state UX
- Comprehensive end-to-end Home Assistant upgrade, entity registry, reset,
  rollback and automation regression tests

## No silent regressions

- No automatic POST, no blind control retries or fallback across unverified routes.
- Keep original V2 entity unique IDs; no duplicate HA devices.
- Preserve historical API-family variants without probing irrelevant paths.
- Save bounded redacted GET evidence, no VIN, S-PIN or bearer token in diagnostics.
- Treat full V2 compatibility as a **release gate**, not a catalog count.
