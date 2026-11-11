# Audi Connect V3 — release acceptance matrix and migration gates

## 3.0.0b3 code gates

| Gate | Automated criterion | Live criterion |
|---|---|---|
| HACS/manifest | Beta version/tag match; hassfest + HACS validation | HACS install/rollback |
| Runtime | V3 coordinator is not a subclass of V2 | Exactly one polling task |
| Transport | Auth boundary only shared; approved CARIAD/GraphQL hosts | Q8 region/credential works |
| Minimal entities | Only Climate, Cloud, Age, Capability, Poll, Refresh | No active old V2 switches |
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
