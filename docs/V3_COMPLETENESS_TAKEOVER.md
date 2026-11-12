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


## Normal HA command cadence

Following user feedback, the ordinary per-vehicle mutation cooldown is now
10 seconds from command initiation (previously 90). This is a local
anti-flood policy, not a measured Audi service limit. Accepted wake/refresh
does not add a normal mutation cooldown; the prior real command retains
its guard. Immediate supported stop actions remain available. Requests
are still serialized; unresolved outcomes block, no auto-retry is added,
and OEM quota/rate limiting remains in force. Engineering experiments retain
the separate stricter 90-second normal-command guard and their own review
and cooldown rules. The wake-specific budget remains unchanged.
Regression tests cover the exact ten-second boundary and restart.


## Additional b12 response normalization review

Both shared selective-status schema inventories were capped at 128 rows.
The union includes climate request operation/status, charging preferred mode,
charging timer timeInCar (vendor sentinel in b12), access overallStatus,
engine-specific fuel and electric measurements, and connected service metadata.
Climate request operation/status are exposed as bounded attributes independent
of physical HVAC state; no request ID or inferred completion is exported.
Preferred charge mode is separate from actual mode. Discovery reports
current-session schema inventory coverage separately from assessed read jobs.
An untruncated captured response is not proof of all OEM variants or complete
semantic mapping.

The b12 warningLights value is only visible as an object, without its children.
Charging profile, readiness, and timer inner schemas are incomplete; a valid
timeInCar example is absent. Low-voltage battery, battery support/care, departure
profiles/timers and auxiliary heating require additional response evidence.
No invented warning list, 12V voltage, departure schema or healthy vehicle
state may be published from this snapshot. The completeness gate remains open.


## Automatic read-only policy

All 23 reviewed selective-status jobs stay in the shared normal GET, including
unknown, unmapped, stale and unadvertised jobs. A supplementary targeted probe
remains bounded; it is not a prerequisite to continued normal polling. Only
explicit job-level unsupported evidence removes a job from the schedule.
Reviewed standalone trip, tripStatistics, parking and legacy resource reads
run automatically on their own quota-aware cadence, without physical-test
consent. A user-disabled GPS tracker is respected. Exact standalone routes
can be excluded by explicit unsupported response, HTTP 405 or 410; a plain
404, 403, 429, missing value or transient error does not prove non-support.
Exclusions persist per vehicle and context and are invalidated on a changed
vehicle context. A later positive response can recover an exclusion.
No numeric Audi error codes are guessed. The unreviewed/custom or
reference-only routes remain outside automatic discovery until reviewed.
GraphQL inventory is read-only despite POST transport. Physical mutations,
including wake/refresh commands, still require explicit user initiation.
Coverage reports distinguish excluded from unknown and observed reads.
This is implementation evidence, not CI or live acceptance.


## Candidate verification — 12 November 2026

Code through `be6a34f480de14a504737d67ff4e1d170ef8c916` passed the complete Python regression suite and HACS/hassfest validation:
- [Regression CI](https://github.com/npinguin/audi_connect_ha/actions/runs/43227013194)
- [HACS/hassfest CI](https://github.com/npinguin/audi_connect_ha/actions/runs/43227013250)

New public-schema fixtures cover Audi charging/departure timers, charging profiles,
battery care, warning/campaign data, readiness, and explicit left/right lights.
Sources: [Audi upstream issue 760](https://github.com/audiconnect/audi_connect_ha/issues/760)
and [Audi JSON Data Structures](https://github.com/audiconnect/audi_connect_ha/wiki/JSON-Data-Structures).
Shared CARIAD battery support enum references (not proof of Audi vehicle support):
[low voltage](https://github.com/tillsteinbach/WeConnect-python/blob/46ce868362772c553d4bef5a7eb84b9765b1dd38/weconnect/elements/lv_battery_status.py)
and [battery support](https://github.com/tillsteinbach/WeConnect-python/blob/46ce868362772c553d4bef5a7eb84b9765b1dd38/weconnect/elements/battery_support_status.py).
Only explicit supported enum values are projected; voltage is not inferred.

Previously open observed field dispositions:
- access overallStatus, door names and window names: structured access attributes.
- charging timer timeInCar: zoned vehicle timestamp only; sentinel remains unknown.
- connected-service id, expirationDate and userDisablingAllowed: typed service attributes.
- primaryEngine currentFuelLevel_pct: explicit fuel-level source, separate from SOC.

The improved per-job collector walks original decoded response types, up to 512
fields/64000 characters per job, with truncation flags. The previous b12 snapshot
cannot be retroactively reconstructed. Canonical scalar mapping coverage is
reported separately from schema capture and read assessment.

Eight regression-proven implementation gates are closed. Seven HACS
evidence gates remain pending: real vehicle identity, endpoint completeness,
remaining departure profile evidence, target health/12V evidence, actual
discovery coverage, untruncated target schema and the candidate evidence matrix.
Live acceptance is separately open. The manifest stays b12 until the machine
gate permits a new version. No published b13, stable promotion or physical
confirmation is asserted. A CI artifact is not a HACS release.
