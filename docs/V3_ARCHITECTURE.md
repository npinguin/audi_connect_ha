# Audi Connect V3 — architecture and ownership

**Status:** canonical community vision and technical design; development remains incomplete. Latest published experimental HACS candidate: 3.0.0b17. V2 remains the default and rollback choice. The subsequent development branch is not an authorized release. The historical b8 baseline below is retained for provenance, not current acceptance.

## Product vision

**Configure → Discover → Use.** The ordinary user's experience should be Configure → Use; discovery is a mostly automatic, progressive runtime phase, not a mandatory technical wizard. The integration should make the best use of available Audi capabilities through native Home Assistant entities and preserve correct behavior across restart, recovery, vehicle models, markets and API generations.

- More supported functionality, less manual configuration. New useful mappings should benefit every compatible vehicle automatically.
- Reliable, truthful states, not guessed identity, fake availability or HTTP success presented as physical confirmation.
- An optional admin Workbench lets the community discover, configure, validate and repair exceptions using the same runtime, not a second integration.
- Lean and maintainable: configuration-first reviewed capabilities; one canonical model, one transport and one command lifecycle. Prefer removing duplication to adding frameworks.

## Core use cases

| ID | End-user / engineering outcome | Acceptance |
| --- | --- | --- |
| GUC | Configure → Discover → Use | Clean installation, progressive native HA functionality, no Workbench required; real vehicle state and control validated. |
| EU01 | Configure | Standard HA authentication, vehicle inclusion/exclusion, optional S-PIN and polling preferences. |
| EU02 | Discover read-only data automatically | Bounded automatic background discovery, progress, completion/reason, restart and recovery; do not wait to publish valid entities. |
| EU03 | Discover controls automatically | Resolve and activate reviewed eligible bindings without physical tests. Optional guided Yes/No verification for unresolved functions, OK/Not OK/Not sure where evidence cannot settle outcome. |
| EU04 | Use and recover | Native sensors, binary sensors, climate, switches and other supported HA platforms/services; preserve config, bindings and IDs through reauth, reload and restart. |
| EU05 | Understand behavior | Availability, freshness, quota, actual polling cadence, retries, pending or uncertain actions and meaningful recovery guidance. |
| EN01 | Inspect the canonical inventory | Capability ↔ attribute/action ↔ API operation/family ↔ actual or intended HA entity; combined filters and navigation. |
| EN02 | Configure and test | Shared definition editor, typed mappings, variants, bounded request/response evidence; immutable revisions and guarded activation. |
| EN03 | Debug and repair | Actual HA state vs normalized observation vs source response, history, test result and comments; Edit API → Retest → Save. |
| EN04 | Validate the golden journey | End-user validation view: same discovery/health/eligibility as native HA, Guided or selective Expert mode; inspect actual HA functionality, not just API calls. |
| EN05 | Reuse and contribute | Portable reviewed definition JSON, sanitized evidence, applicability, regression tests and reviewed catalog promotion. |

Detailed engineering use cases and open acceptance points are in [the runtime engineering workflow](V3_RUNTIME_ENGINEERING_WORKFLOW.md). The binding discovery and safety rules are in [ADR 002](V3_ADR_002_FAST_DISCOVERY.md).

## Technical architecture

```text
Normal HA setup / entities / services / automations       Admin Workbench
               |                                               |
               +-------------- shared runtime contracts --------+
                                        |
                          V3Engine + HA coordinator
                       /                 |                  \
                Vehicle identity      Status engine       Command engine
                  & context          & read discovery     & verification
                       \                 |                  /
                         Canonical capability / operation catalog
                         Typed mappings + per-vehicle profiles
                                        |
                        Auth / transport / quota / family executors
                              CARIAD | MBB | GraphQL
                                        |
                                    Audi cloud
```

The HA coordinator schedules ordinary polling and background discovery. The Status engine reuses batch reads, applies typed conversion and freshness rules, and publishes through native HA entities. The Command engine owns current eligibility, intent, durable journaling, one-shot dispatch, cooldown, readback and review. Profiles retain private vehicle bindings and bounded evidence; no second persistent wizard or telemetry model. Shared account authentication is the sole token owner. V2 remains an independent business runtime and rollback choice, not an invisible fallback for V3 commands.

Canonical relations: capability contains semantic attributes and actions; operations define reviewed family/method/path/request/response contracts; bindings resolve a vehicle's applicable operation and mapping; HA entities are projections of these contracts. Request/reply evidence and manual reviews are separate from runtime authority. A normal read-only discovery scan must never physically actuate or wake the vehicle.

### Workbench — five views, one backend

| View | Purpose |
| --- | --- |
| Overview | Vehicle context, health, coverage and findings |
| Capabilities | Functional inventory, attributes, actions, HA links |
| Configure & Test | Existing definition editor, variants, transformations and explicit tests |
| API Log | Bounded masked executions, filters, reviews and source evidence |
| End-user validation | Reproduce Configure → Discover → Use, guided or selectively in Expert mode; edit failed API in Configure & Test |

Expert mode is not a requirement for normal setup. Unknown endpoints, unsupported auth contexts and sensitive commands remain restricted. New API-family support requires reviewed code-owned auth and transport contracts, not arbitrary credential forwarding.

## Delivery roadmap and acceptance

| Order | Focus | Current development status (not release certification) |
| --- | --- | --- |
| 1 | Canonical model and simplicity | Shared catalog, typed mappings and executor separation exist; consolidation and parity review remain open. |
| 2 | Engineering editor | Shared read/control/GraphQL editor and definition JSON copy/paste implemented; full lifecycle and tests remain. |
| 3 | End-user golden use case | Native setup, bounded automatic reads and reviewed control resolution exist; guided/selective validation added. Shared completion/pause/retry status, native guided consent, explicit unresolved-read recovery and guarded charging-equivalent testing are implemented in development. Full-catalog synthetic Configure → Discover → Use → Restart regression passes; real HA/vehicle acceptance remains. |
| 4 | Identity and functional completeness | OEM identity is a priority: native GraphQL metadata can be null, even when VIN inventory succeeds. Reviewed same-VIN OEM candidate adoption and subsequent source refresh are implemented in development; actual clean-install manufacturer identity evidence is still missing. Trips, structured details, health and full schema disposition require verification. |
| 5 | Evidence, lifecycle and reuse | Shared log and entity traceability, private reviews and draft removal exist; full trace, revision, rollback and portable contribution validation remain. |
| 6 | Quality and upstream | Exact-SHA CI, V2 delta register, dependency/ownership checks, tests, documentation and upstream reconciliation. |
| 7 | HACS acceptance | Close implementation/evidence gates, prove static parity, package/install validation and the golden journey; stable/upstream promotion additionally requires real supported-context and rollback proof. |

This roadmap is a direction, not a claim of completed implementation. The latest published experimental exception is 3.0.0b17; the development branch contains subsequent changes that have not been released. [Machine-readable completeness gate](../governance/V3_COMPLETENESS_GATE.json), [parity gate](V2_V3_PARITY_BASELINE.json), [closure plan](V3_ARCHITECTURE_CLOSURE.md), [community guide](V3_COMMUNITY_HOWTO.md).

## Historical implementation baseline (b8)

One integration, one HA config entry, one shared Audi account/token owner, one active V2 or V3 runtime. V3 independently owns the vehicle inventory, polling, mapping, commands and all nine native HA platforms. The integration registers the existing service IDs in both runtimes and routes by VIN to the selected runtime. Unsupported V3 commands fail explicitly; no hidden V2 business fallback. User-disabled registry entries remain untouched; integration-disabled entries from the earlier experimental migration are restored.

The historical b8 baseline contains seven capability groups, 59 API operations (33 GET, 22 POST, 4 PUT), 109 historical entity rows plus one additional last-trip row, and 796 passing Python tests. Inventory counts and green CI do not establish parity or physical acceptance. The release gate is still closed.

Historical b8 debt (not a current defect inventory): climate-specific polling/profile persistence, a 1,290-line engine, redundant pilot runtime and catalog, overlapping read/command schemas, parameterized custom commands not activatable, nonpersistent normal command context, quota recovery and token-refresh concurrency, incomplete multi-car lifecycle, V2 upstream deltas and stale generated inventories.

## Module ownership and dependency rules

The engine is a composition root and lifecycle orchestrator, not a business logic container. Status and Command have separate execution rules and share the same typed catalog, vehicle context, bindings and transport. V2 and V3 share account authentication, config entry and HA identity only; V2 business behavior remains near-upstream. OEM legacy API families remain supported; obsolete V3 pilot implementations do not.

| Owner | Owns | Does not own |
|---|---|---|
| Engine | Composition, startup, refresh orchestration, shutdown | OEM endpoints, payloads, business rules |
| Catalog | Capability, attribute, command, operation definitions and validation | HTTP, mutable vehicle state |
| Vehicle | Inventory, identity, current observation state, reconciliation | Command dispatch, route definitions |
| Status | Read-only discovery, polling plan, extraction, normalization, freshness | Mutating requests, HA entities |
| Command | Eligibility, engineering tests, fast control resolution, execution, journal and confirmation | Direct HA state changes, transport credentials |
| API | Auth lock/token rotation, transport, quota and family executors | Vehicle business rules, entities |
| Profiles | Vehicle bindings, evidence persistence, schema migration | Network discovery, dispatch |
| HA | Entity/service projection, stable IDs, registry, recorder semantics | OEM endpoints and route selection |
| Workbench | Admin UI for editing, testing, review, activation via public APIs | Direct Audi requests or a second execution engine |
| Diagnostics | Bounded redacted snapshots and reports | Runtime decisions |

Dependencies flow from HA/Workbench to public runtime contracts, to Vehicle/Status/Command, then Catalog/Profiles/API. Modules cannot import the composition root or HA projection from the domain layer. Diagnostics consumes public snapshots only. Typed contracts and dependency checks must be enforced in CI.

## Canonical domain concepts

- Capability: functional grouping, independent of API family.
- Attribute: semantic value, type, unit, freshness policy and optional HA projection.
- Command: semantic action, typed parameters, eligibility/security and confirmation policy.
- API operation: approved family, method, route/template, delivery, mapping and optional code-owned handler.
- Vehicle binding: vehicle-specific selected operation, provenance/evidence and allowed parameters.

A basic capability, attribute or approved operation is configurable without changing the generic engine. Shared batch GETs are API optimization, never owned by climate. Use one validation/resolution model; no duplicated route catalogs or evidence stores. Specialized OEM flows (MBB challenge-response, read-modify-write settings, trip calculation) remain code-owned handlers with explicit contracts.

## Discovery — two product modes

The authoritative policy is [ADR 002 — engineering discovery and automatic fast discovery](V3_ADR_002_FAST_DISCOVERY.md).

Engineering: admin-only Workbench provides selective testing of explicitly authorized functions and direct operation editing. The same guided discovery can be reproduced in End-user validation, with selective Expert mode and Edit API on failure. Persist attempts before dispatch, distinguish physical outcome from backend results, and promote suitable evidence into reviewed catalog rules. Experimental custom definitions remain private until reviewed.

End-user: automatic fast discovery after installation, startup and relevant context change, with no required Workbench or manual test per control. Reuse applicable verified local bindings and reviewed catalog evidence; match current vehicle/auth/region/capabilities, permissions and required state using bounded read-only discovery. Automatically expose eligible known controls with stable HA identities. Unknown or contradictory cases remain unverified/unavailable, not permanently unsupported. No automatic physical action, POST/PUT probing, wake or mutating retry. An actual user or explicitly configured HA automation invokes a normal command through the same command engine.

## Reliability and compatibility

Normal and experimental commands use one persistent lifecycle. Persist before mutation, send once, distinguish transport acceptance, backend completion and physical verification, retain uncertainty across restart. Confirm via bounded reads or explicit human verification where physical readback is unavailable. Per-vehicle command exclusion and account quota protection are mandatory. Never re-send merely because an earlier result is unknown.

Quota values have a lifecycle (observation time, trustworthy reset/retry-after if available, bounded recovery); stale reserve must not cause permanent suspension. Serialize token refresh per account. Reconcile new/removed vehicles without deleting registry history based on an incomplete cloud response. Keep last-known telemetry with clear freshness; do not infer current safety state from stale values.

## Engineering and acceptance

See [Architecture Closure plan](V3_ARCHITECTURE_CLOSURE.md), [configuration](V3_CONFIGURATION.md), [development profiles](V3_DEVELOPMENT_PROFILES.md), [HA identity contract](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md), [test matrix](V3_TEST_MATRIX.md) and [parity baseline](V2_V3_PARITY_BASELINE.json).

All work stays on `feature/v3-clean-discovery`. No new permanent development branches or extra runtime. Static parity and code-complete acceptance precede beta publication; physical vehicle acceptance and V2/V3 rollback precede stable promotion. Historical release notes remain historical and are not the target architecture.

## b10 product projection

Historical parity protects identity, not incorrect category or duplicate default presentation. The b10 product projection uses reversible compatibility hiding, explicit vehicle categories and conditional drivetrain-source resolution. See the b10 release notes for limitations.
