# V3 completeness audit — development after b12

## Release decision

HACS b12 remains immutable. No next beta until the implementation, field-disposition and regression gates in `governance/V3_COMPLETENESS_GATE.json` are closed. Physical acceptance of a new build is an independent upstream gate. An unobserved job is not proof of unsupported capability.

## Evidence and gaps

The sanitized b12 evidence snapshot is in [V3_COMPLETENESS_EVIDENCE_B12.json](V3_COMPLETENESS_EVIDENCE_B12.json). It contains structural field paths, types, dispositions and capability/operation evidence, not raw responses, VIN, account identifiers, positions or trip values.

- 23 known jobs: 14 observed, 9 not observed.
- 95 registered identities: 56 projected/available, 11 projected/unavailable, 16 not projected, 12 disabled.
- All three trip endpoints and parking returned HTTP 200; climate batch HTTP 207 with valid recognized schema; two individual climate probes HTTP 207 with invalid mapped schema.
- Physical route evidence in b12: climate stored start and stop worked. Start with settings and unlock HTTP 200, wake HTTP 204; none is a substitute for separately recorded physical confirmation.
- Schema sample is truncated; the evidence ledger is not a complete enumeration of the real response.

Development currently contains 139 product entity identities and 62 reviewed catalog operations. These are inventory sizes, not a promise that every vehicle supports them.

## Implementation and acceptance matrix

| Capability | Development additions and remaining work | Actual b12 evidence |
|---|---|---|
| Climate | Native control; accepted-command projection; staged/reported target; window heating status and switch; timer structures still need normalized details | Stored start/stop physically confirmed; parameterized start HTTP 200; delayed telemetry |
| Charging | Native switch, SOC and mode/settings; structured charging profiles/timers and departure details remain open | Charging/profile/timer jobs observed; write commands catalog-matched, not physically confirmed |
| Access | Native lock, component sensors, accurate aggregates and icons; normalized details and partial evidence review | Access job observed; unlock HTTP 200, physical evidence absent |
| Vehicle status | Localized model inventory, independent powertrain, alternate range/SOC/odometer, boolean oil; capability expiry/health/details remain open | Model family empty; hybrid trip enum; boolean oil; observed fields truncated |
| Mobility | Last, short and long trip metrics; normalized observed history; durable coverage/backfill still open | Three trip GETs and parking HTTP 200; historical array unsorted |
| Service | Inspection, oil service and odometer; health warning mapping remains open | Maintenance job observed; health warnings job observed |
| Remote | Safe fixed read discovery; one-shot actions; explicit security restrictions | Wake HTTP 204; flash/refresh not physically confirmed; engine actions ineligible |

## Required upstream release evidence

Publish a model/auth/region-scoped matrix per capability, semantic action and route with separate columns for implementation, automated regression result, HTTP execution, schema validation, live telemetry readback and physical confirmation. Mark unknown/unobserved/not applicable separately; do not mark a catalog route as tested just because its capability is enabled. Attach exact release SHA, migration/rollback tests and privacy-safe field-disposition report. Never import personal raw trip or location data into the public report.

## Current blockers

See machine-readable gate. Implemented-pending-validation means committed but not closed. Live manufacturer media must be confirmed after locale correction. HACS readiness requires code, complete reviewed disposition, tests and a documented physical acceptance plan; upstream readiness requires physical acceptance evidence and explicit limitations.
