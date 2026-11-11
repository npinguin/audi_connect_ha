# Audi Connect V3 — release acceptance matrix and migration gates

## 3.0.0b5 discovery test gates

| Gate | Automated criterion | Live criterion |
|---|---|---|
| HACS/manifest | Beta version/tag match; hassfest + HACS validation | HACS install/rollback |
| Runtime | V3 coordinator is not a subclass of V2 | Exactly one polling task |
| Transport | Auth boundary only shared; approved CARIAD/GraphQL hosts | Q8 region/credential works |
| Minimal entities | Climate, Cloud, Age, Capability, Poll, Refresh plus discovered read-only sensors/binary sensors | No active old V2 switches |
| Entity IDs | Climate/cloud/age IDs preserved | No broken automations after V2 rollback |
| Status discovery | GET schema/freshness and alternatives; 429 inconclusive | Valid Q8 climate state & timestamp |
| Control test | Requires user click and post-action confirmation | Q8 Start / Stop physically verified |
| Custom API paths | Relative hosts, known auth families, typed parameters | New route can be tested from UI |
| Profile storage | Versioned, local, per vehicle; partial save safe | Survives HA restart |
| Diagnostics | No raw VINs/tokens or full responses | Export reviewed locally |
| Rate limits | Quota reserve, no auto wake; no POST retries | API usage stable |
| V2 rollback | Only migration-disabled old entities restored | V2 feature set returns |

## Review before every capability migration

Define stable ID/units/response mapping and optional Status/Control; map
one or more API operation candidates; build synthetic success/partial/error
examples; apply the V3 route resolver and evidence store; preserve the
historical unique ID; verify both HA states and domain actions on a real
vehicle. Add focused unit tests and a regression guard. Never expose a
half-working entity because a single response happened to return 200.

The current historic backlog, in intended order: charging telemetry,
charging controls, vehicle core/health, lock/access, trips/consumption,
other actuators and legacy market adapters. Reuse the same V3 branch/PR
and release independently verified vertical slices as subsequent betas.

## Next engineer: read-only discovery

Extend the capability inventory using historic V2 job and researched API paths. Record attribute, family, method, route, response mapping, capture time, freshness and tested outcome per vehicle. V2 references are not proof of V3 support. Maintain the single-package V2/V3 switch.

## 3.0.0b6 additional discovery and remote-control gates

- V3 startup auto-discovery must issue only bounded CARIAD GET requests.
- Workbench uses native HA body fonts and filters by vehicle API family.
- Wake-up, charging start/stop, window heating start/stop, climate ON/OFF and
  access lock/unlock have explicit CARIAD routes and per-vehicle evidence.
- Never POST on startup or due to a route not being found. No automatic fallback
  from charging/start to charging/start-stop.
- Only an explicit human-selected control test can POST once. Afterward the
  operator must verify the physical vehicle action before activation.
- S-PIN is required for lock/unlock, used only inside the explicit request,
  and excluded from diagnostics and Workbench response previews.
- HA buttons, quick climate switch and lock reuse the old V2 unique IDs and
  are created only after human verification. Door Lock additionally requires
  a readable current door state, so unknown must not mean unlocked.
- V2 rollback, legacy MBB and still-unmapped V2 controls remain separate tests.
\n## 3.0.0b7 — declarative API metadata & upstream command parity
- Sensor units, HA device classes, state classes and precision come from
  `v3/attribute_contracts.json`, transcribed from stable V2 descriptors.
- The API layer owns source conversion through `v3/api_value_mappings.json`
  and safe per-route conversion declarations; HA's standard unit converters
  handle units. Unverified source units are not guessed.
- GET extraction uses RFC 6901 JSON Pointer and preserves legacy V2 dotted
  paths. A numeric zero and Boolean false must survive.
- A route cannot map SoC into a distance unit or run arbitrary expressions.
- Regression tests assert the exact CARIAD HTTP method, path and JSON body
  for Climate Start (none), Climate Stop (none) and Wake-up (empty JSON).
- POSTs still require an explicitly selected control, one request, physical
  confirmation and no automatic retry.
- API responses stored in private profiles remain bounded and redacted.
- Known outstanding gaps are tracked in `V3_FEATURE_GAPS_3.0.0b7.md`.
