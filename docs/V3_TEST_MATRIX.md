# Audi Connect V3 — release acceptance matrix and migration gates

**Current target:** the Architecture Closure and ADR 002 gates below supersede historical b5–b7 gates where they conflict, especially mandatory manual activation for end users. Historical sections describe previous releases.

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


## Architecture Closure — mandatory target gates

| Gate | Automated acceptance | Live/engineering acceptance |
|---|---|---|
| Module ownership | AST/import boundaries, no cycles, typed public contracts; composition root has no domain dispatch | Owner review of exceptions |
| Generic catalog | Add synthetic capability/attribute and approved GET/POST/PUT via definitions without changing generic engine | New route in Workbench |
| Status | Multi-capability batch dedup, stale/out-of-order/207/429 and unknown-state tests | Parked-car observations and quota evidence |
| Engineering discovery | One exact explicit action; journal persisted before dispatch; uncertainty and restart tested | Physical review, versioned reusable evidence |
| End-user fast discovery | Fresh setup and warm restart auto-expose eligible known controls, no Workbench or manual test; no physical mutations in discovery; only reviewed read-only inventory query exception | Clean onboarding on supported real vehicle contexts |
| Eligibility | Catalog match vs local physical proof distinguished; changed context/revision, negative evidence, disable, credentials and stale state respected | Q8 and applicable MBB/other contexts |
| Command lifecycle | Typed parameters, persistent pending/cooldown, no duplicate mutation after timeout/cancel/restart, backend vs readback | Authorized actual control and observed result |
| API | Concurrent auth refresh, quota exhaustion/recovery, bounded probes and transport allowlist | Account request budget stable |
| HA lifecycle | Dynamic multi-car entities, stable IDs, registry/user-disable/recorder, setup/unload/reload | V2→V3→V2 actual rollback |
| V2 | All deviations against upstream explicitly governed and regression-tested | Existing V2 behavior preserved |
| Quality | Lint/format, type contracts, risk-based coverage, generated inventory parity, full CI | Architecture closure review |

Static code-complete parity before beta publication; physical vehicle and rollback acceptance before stable. No release gate is changed by documentation.

### Explicit b8 experimental test exception

One supervised HACS prerelease is authorized before static parity completion. This does not mark any acceptance row passed, change the standard code-complete beta policy, or permit stable publication. See b8 release notes and the version-bound authorization record.

## b10+ test governance — current product contracts override historical presentation

- Historical V2 inventory is an identity and rollback baseline, not an oracle for V3 categories, icons, visibility or duplicated functionality.
- Test product behaviour through HA platform projection, native entity properties, registry migration and public command/status boundaries. Source-text checks are reserved for architectural/packaging boundaries, not business behaviour.
- A changed requirement requires explicit contract and test updates together. Never change expected results merely to match a failing implementation. Preserve negative cases and add an independent behavioural assertion.
- For entity rationalisation, require no evidence/no entity, invalid type/no numeric entity, valid zero, repeat-discovery deduplication, read/write gating, vehicle category, user registry overrides and reversible migration. Actual HA installation and rollback remain separate live acceptance.
- The b10 release candidate failure (826 passed, two failed) is recorded in its notes. Subsequent test-only improvements are independently validated; an immutable published release is never rewritten.

### Maintainability rules

One product contract per entity; metadata references resolve from the owning catalog rather than duplicated category lists. Native projection and registry migration consume the same category policy. Use named behavioral tests and realistic fixtures; retain source checks only for actual architecture/packaging constraints. Keep historical release notes immutable and current acceptance criteria separate. Avoid release-specific implementation names in new tests unless validating migration from that version.

Observed job freshness must not be masked by a newer unrelated capture. Age retains the newest-capture meaning for compatibility; freshness is conservative across observed jobs, not proof of unobserved coverage. Response field samples must report truncation; timestamp metadata must not be reported as a missing functional entity.

Capability job ownership is derived from the existing historical inventory (not a second UI mapping). Diagnostics include all catalog capabilities and safe built-in operation/command evidence; live eligibility is distinct from physical proof, custom names are masked, and no raw request/response history is exported.

Release metadata regression tests derive the active beta version from the manifest and independently check the matching authorization, notes, package/checksum names, workflow intent and exact-parent guard. Do not hardcode a prior beta in reusable tests. Keep the V2 delta blob register synchronized with the actual manifest; its exact comparison remains mandatory.

Stateful operational controls use the central capability/action bindings, explicit status evidence, unknown on stale or pre-command capture, and no optimistic state. Window heating reads front/rear operational state, never a preference or legacy mirror state. Existing buttons remain compatible; only their default visibility changes when the switch is supported. Inventory model metadata is tested independently from nickname and live captures.

Accepted-command projection tests must cover old capture, newer contradictory capture, failure, expiry, restart uncertainty, independent controls and immediate explicit stop. Never mutate telemetry or mark a command physically verified from HTTP alone. Native lock uses pending transition rather than assumed physical lock.

Modern trip regression fixtures cover the actual observed b12 fields `averageElectricConsumption`, `totalElectricConsumption_kwh` and `totalFuelConsumption_L`. Explicit total units are preserved; the unsuffixed electric average is accepted only when corroborated by distance and total. Zero is valid, boolean is not numeric, and legacy scaling must not leak into modern normalization.
