# V3 b12 completeness takeover — test candidate work in progress

Baseline: installed 3.0.0b12. Target: next immutable V3 HACS test release only
after the existing completeness gate permits it. V2 remains default and rollback.
No manifest bump, tag, HACS publication or upstream promotion is authorized by this document.

## Changes in the development branch

- Private normalized modern CARIAD trip archive, per config entry and vehicle,
  retained across restart and rollback. Up to 10,000 observed trips; 50 most
  recent rows in the HA entity, full archive available via paginated admin
  `audiconnect/v3/trip_history` (offset/limit). Explicit config entry removal
  removes the private archive. No raw trip IDs, coordinates or credentials.
  Native trip metrics can use normal HA Recorder prospectively; no historical
  backdating of Recorder. Long-term cumulative trip windows are separate.
- Explicit component identity for parking lights and invalidation of partial
  or contradictory door/window reports; disabled preferred charging windows
  cannot be projected as active windows.
- Structured charging/climate/ventilation timers, door/window/light rows,
  access overall status, and connected-service ID, expiry and disable
  eligibility; attached to existing native product entities.
- Alternate active-ventilation timer namespace is read evidence, not permission
  for ventilation actuation.
- Charging parameter writes require parameter-specific read evidence in addition
  to generic charging capability; existing request validation remains in force.
- Model entity identity survives missing inventory; no nickname-as-model or
  fabricated manufacturer label. Existing HA device model updates when a real
  inventory label becomes available.
- Diagnostics distinguish visible built-in operations from engineering counts,
  report actual HA units/device/state classes, provide per-job and inventory
  structural evidence, withhold personal trip previews.
- New regression tests for trip archive roundtrip, duplicate merge, malformed
  rows, partial access, parking lights, structured details, schema privacy,
  charging eligibility and alternate ventilation discovery.

## Capability/evidence matrix (installed b12 snapshot, not candidate validation)

| Capability | Read evidence | Write evidence | Candidate status |
|---|---|---|---|
| Identity | GraphQL model absent in snapshot; trip type hybrid | N/A | Locale and stable projection implemented; real OEM label must be checked |
| Access | 18/20 attributes verified by runtime | Unlock HTTP 200; no physical confirmation | Partial/contradictory component correction implemented; complete schema pending |
| Charging | 11 stale, 9 not tested, 1 mapping pending | No physical confirmation | Parameter-specific eligibility, profiles/timers details; fresh vehicle data and controls pending |
| Climate | Batch HTTP 207 valid; targeted probe invalid | Stored start/stop physically confirmed; start with settings HTTP only | Timer/window details and prior command projection; readback and physical tests pending |
| Mobility | Three trip GETs HTTP 200, parking HTTP 200 | N/A | Archive and native metrics; endpoint completeness/retention validation pending |
| Service/health | Inspection 5 verified; warning structure present | N/A | Full warning/12V schema and normalized health details unresolved |
| Remote | Wake HTTP 204; flash advertised | No physical confirmation | Explicit testing pending |
| Connected services | Capability ID, expiry, disabling flag observed | No write authorization from these fields | Structured attributes implemented; validation pending |

HTTP success, valid response schema, fresh vehicle capture, backend readback,
and physical confirmation are different evidence levels. A generic hybrid
label is not proof of PHEV subtype. No other model or region is certified by
this single-vehicle snapshot.

## Remaining release conditions

The canonical machine gate is `governance/V3_COMPLETENESS_GATE.json`. No
closure evidence is manufactured here. In particular: complete remaining
response schemas (health warnings, low-voltage battery, departure timers/profiles,
unobserved jobs, identity inventory), resolve timer recurrence and warning
semantics, registry lifecycle and V2 rollback, candidate regression tests,
and upstream evidence matrix. Physical validation remains separate.

The new tests are committed; this record does not assert a successful CI run.


## Additional b12 runtime finding: wake cooldown (12 November)

A user explicitly woke the Q8, received a successful cloud poll, then could
not set HVAC mode because the preceding wake activated the 90-second global
mutation cooldown. Reviewed CARIAD wake/refresh acceptance now permits the
next normal HA action without a wake-induced cooldown. An earlier actual
mutation still owns its cooldown and immediate stop exception. Uncertain
commands, stricter engineering experiment gates, serialized dispatch and the
existing wake-specific 30-minute/four-per-day budget remain unchanged.
Readback of the preceding actual action is not hidden by a linked refresh.
Regression tests cover both wake endpoints, HTTP 204, repeated wake limits,
uncertainty and linked-refresh masking. Candidate CI and live acceptance
remain pending.
