# Audi Connect V3 — architecture and ownership

**Historical architecture baseline:** 3.0.0b8 source, consolidated commit `284230a5deb3cc0e9366e26c96c87667f2d95a68`, 12 November 2026. **Target:** architecture closure, approved design direction; implementation incomplete. V2 is still the default and rollback choice. The b8 baseline is historical; b12 is a separately authorized experimental HACS test, not stable or static parity sign-off. See current implementation progress and b12 release notes.

## Current implementation (AS-IS)

One integration, one HA config entry, one shared Audi account/token owner, one active V2 or V3 runtime. V3 independently owns the vehicle inventory, polling, mapping, commands and all nine native HA platforms. The integration registers the existing service IDs in both runtimes and routes by VIN to the selected runtime. Unsupported V3 commands fail explicitly; no hidden V2 business fallback. User-disabled registry entries remain untouched; integration-disabled entries from the earlier experimental migration are restored.

The historical b8 baseline contains seven capability groups, 59 API operations (33 GET, 22 POST, 4 PUT), 109 historical entity rows plus one additional last-trip row, and 796 passing Python tests. Inventory counts and green CI do not establish parity or physical acceptance. The release gate is still closed.

Known debt: climate-specific polling/profile persistence, a 1,290-line engine, redundant pilot runtime and catalog, overlapping read/command schemas, parameterized custom commands not activatable, nonpersistent normal command context, quota recovery and token-refresh concurrency, incomplete multi-car lifecycle, V2 upstream deltas and stale generated inventories.

## Target (TO-BE)

```text
HA entities / services / administrator Workbench
                 |
       V3Engine (composition & lifecycle)
                 |
       Vehicle / Status / Command
                 |
       Catalog / Profiles / API
                 |
       CARIAD / MBB / GraphQL
```

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

Engineering: admin-only Workbench manually tests one explicitly chosen operation on one vehicle, persists the attempt before dispatch, records backend outcome and physical review, and promotes suitable evidence into reviewed, versioned catalog rules. Experimental custom definitions are private until reviewed.

End-user: automatic fast discovery after installation, startup and relevant context change, with no required Workbench or manual test per control. Reuse applicable verified local bindings and reviewed catalog evidence; match current vehicle/auth/region/capabilities, permissions and required state using bounded read-only discovery. Automatically expose eligible known controls with stable HA identities. Unknown or contradictory cases remain unverified/unavailable, not permanently unsupported. No automatic physical action, POST/PUT probing, wake or mutating retry. An actual user or explicitly configured HA automation invokes a normal command through the same command engine.

## Reliability and compatibility

Normal and experimental commands use one persistent lifecycle. Persist before mutation, send once, distinguish transport acceptance, backend completion and physical verification, retain uncertainty across restart. Confirm via bounded reads or explicit human verification where physical readback is unavailable. Per-vehicle command exclusion and account quota protection are mandatory. Never re-send merely because an earlier result is unknown.

Quota values have a lifecycle (observation time, trustworthy reset/retry-after if available, bounded recovery); stale reserve must not cause permanent suspension. Serialize token refresh per account. Reconcile new/removed vehicles without deleting registry history based on an incomplete cloud response. Keep last-known telemetry with clear freshness; do not infer current safety state from stale values.

## Engineering and acceptance

See [Architecture Closure plan](V3_ARCHITECTURE_CLOSURE.md), [configuration](V3_CONFIGURATION.md), [development profiles](V3_DEVELOPMENT_PROFILES.md), [HA identity contract](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md), [test matrix](V3_TEST_MATRIX.md) and [parity baseline](V2_V3_PARITY_BASELINE.json).

All work stays on `feature/v3-clean-discovery`. No new permanent development branches or extra runtime. Static parity and code-complete acceptance precede beta publication; physical vehicle acceptance and V2/V3 rollback precede stable promotion. Historical release notes remain historical and are not the target architecture.

## b10 product projection

Historical parity protects identity, not incorrect category or duplicate default presentation. The b10 product projection uses reversible compatibility hiding, explicit vehicle categories and conditional drivetrain-source resolution. See the b10 release notes for limitations.
