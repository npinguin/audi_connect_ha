# Audi Connect V3 — Final Architecture Closure

**Status:** accepted engineering direction; work packages open. Canonical branch: `feature/v3-clean-discovery`. Baseline: `284230a5deb3cc0e9366e26c96c87667f2d95a68` (3.0.0b8, 796 Python tests passed). Do not create a V4, parallel runtime or permanent feature branches. No beta/stable publication before the relevant gates.

## Scope and ownership

Follow [V3 Architecture](V3_ARCHITECTURE.md) and [ADR 002](V3_ADR_002_FAST_DISCOVERY.md). The target layout below is a proposed organization, not a claim that these paths already exist. Keep the minimum number of modules consistent with clear ownership; reuse existing implementations and preserve public HA contracts.

```text
v3/
  engine.py                 # composition and lifecycle only
  coordinator.py            # clean HA scheduling adapter
  contracts.py              # stable typed boundaries
  catalog/                  # registry, validation, capability definitions
  vehicle/                  # inventory, state
  status/                   # polling, discovery, mapping, freshness, handlers
  command/                  # executor, policy, discovery, lifecycle, handlers
  api/                      # auth, transport, quota, CARIAD/MBB/GraphQL
  profiles/                 # bindings, evidence, storage and migrations
  ha/                       # platform projection, entities, services, registry
  workbench/                # admin API and frontend
  diagnostics/              # report and redaction
```

### Migration ownership

| Current sources | Target owner |
|---|---|
| engine.py | Engine / Vehicle / Status / Command, extract responsibilities |
| registry.py, full_catalog.json, historical_catalog.py, attribute_contracts.json | Catalog; merge duplicated definitions |
| attribute_runtime.py, read_discovery.py, attribute_routes.py, legacy_read_mappings.py | Status + canonical Catalog validator |
| derived_values.py, legacy_values.py, trips.py, parking.py, freshness.py | Status handlers and Vehicle observation contract |
| action_discovery.py, command_policy.py, command_payloads.py, legacy_commands.py, request_status.py | Command; one lifecycle |
| auth.py, transport.py, family_executors.py | API |
| development_profiles.py, profile_store.py, api_observations.py | Profiles; evidence and journal storage |
| vehicle.py | Vehicle |
| entities.py, ha_platforms.py, service_commands.py, registry_lifecycle.py | HA |
| dashboard.py, frontend/panel.js | Workbench |
| response_preview.py, capability_status.py | Diagnostics/public status report |

Remove obsolete pilot `V3Runtime`, `AudiV3Coordinator`, old climate implementation/catalog and tests after migrating remaining constants, options, helpers and contracts. Do not remove MBB protocol support or the V2 rollback runtime. Migrate persisted profiles/configuration explicitly; preserve entity IDs and user-disabled states.

## Canonical contracts

One catalog with Capability, Attribute, Command, API Operation and Vehicle Binding. A simple new attribute defines type, unit, freshness, availability, HA metadata and stable entity key; operation definitions provide relative approved path, method, family and response mapping. An operation can map multiple attributes. A command defines typed parameters (ranges, units, enums, required/default rules), eligibility and confirmation policy; code-owned handlers perform special OEM transactions.

Status flow: resolve → plan/deduplicate → execute read → normalize/map → validate schema/freshness → commit observation → record evidence. No climate-specific generic engine logic. Keep timestamp order, zero/false semantics and last-known vs active state policy.

Command flow: requested → validated → pending (persisted before dispatch) → dispatched/accepted_unconfirmed → backend_completed → verified where physical readback is possible. Also rejected/uncertain/expired. Unconfirmed flash/horn cannot be marked physically verified without evidence. Journal contains command ID, vehicle binding, redacted parameters, operation revision, timestamps, request ID and outcome; never secrets or raw payloads. Per-VIN exclusion and persistent cooldown, one mutation, no retry on timeout/restart; bounded read-only reconciliation. HA and Workbench invoke the same executor. Acknowledgement alone never updates observed vehicle state as if verified.

## Delivery sequence and acceptance

| WP | Owner/scope | Required result and gate |
|---|---|---|
| WP0 Freeze/baseline | Governance, catalog, V2 | Pin baseline; explicit upstream delta, ownership/dependencies and test inventory; preserve behavior |
| WP1 API foundation | API | Serialize account auth refresh; quota state and bounded reset/recovery with timestamps, retry-after and single recovery probe; family contracts; tests for concurrency, exhaustion, timeout/cancellation |
| WP2 Catalog & Status | Catalog, Status, Vehicle | One schema, generic multi-capability poll/discovery, dedup GET, mapping/freshness and vehicle state; new simple synthetic capability without engine code changes |
| WP3 Command | Command, Profiles | Shared persistent command journal and lifecycle, typed parameters, approved PUT and safe specialized handlers; restart, cancellation, uncertainty, duplicate and readback tests |
| WP4 Profiles & discovery UX | Profiles, Workbench, Command | Manual engineering discovery plus automatic end-user fast discovery per ADR 002; reviewed evidence promotion, binding migration, config-first extensions; no automatic actuator testing |
| WP5 HA & V2 alignment | HA, Vehicle, V2 | Dynamic entity lifecycle across nine platforms; identity, recorder, services and rollback; explicit near-upstream delta and removal of experimental V2 functionality |
| WP6 Cleanup & quality | All module owners | Remove obsolete pilot paths/tests/options; no duplicate definitions or route engines; update canonical docs and generated parity; enforce ownership, dependency, lint/type and quality gates |
| WP7 Acceptance | All | Static applicability/parity and exact-SHA CI before beta; physical supported-context validation and V2→V3→V2 before stable |

Refactor incrementally on the canonical branch. Each slice carries its migration, tests, documentation and cleanup; no permanent compatibility shims in V3. Preserve the 796-test baseline where contracts still apply; replace obsolete pilot tests with current contract tests. New features are subordinate to closure.

## V2 upstream delta

Current upstream master/dev is 2.5.2 (`d12f74c35c1c961f3b040e5cc77acbca2a5cca26`). At audit, seven of 32 upstream integration files outside V3 were unchanged, 25 modified and eight extra files existed. File differences are not semantic parity. Classify each deviation as required HA/runtime/auth seam, justified reliability fix, upstream contribution, metadata or unnecessary fork behavior. Keep explicit reason, owner, tests, upstream issue/PR and exit strategy. Rebase/reconcile accepted upstream fixes rather than maintain duplicate implementations. Protect external PR #915 and research PR #916; neither is a V3 development base.

## Governance and quality gates

Proposed machine-readable artifacts: `governance/OWNERSHIP.json`, `DEPENDENCIES.json`, `UPSTREAM_V2_DELTA.json`, `QUALITY_GATES.json`. These are implementation deliverables, not existing gates. Enforce import/AST dependency direction, no cycles, lint/format, typed public contracts, risk-based coverage, HA lifecycle tests, generated parity/catalog inventories and no unexplained V2 drift. Exact-SHA pytest, Workbench, hassfest and HACS remain required. Do not assert coverage from source strings alone.

## Definition of Done

- Exactly one runtime per config entry; modular ownership and no old V3 pilot.
- V2 near-upstream behavior with all deviations explicitly governed.
- New simple capability, attribute and approved GET/POST/PUT configuration requires no generic engine change.
- One status resolver and one persistent command lifecycle, including typed persistent bindings and restart recovery.
- Manual engineering discovery generates reviewed reusable compatibility evidence; end-user fast discovery automatically exposes applicable known controls without physical actions or required Workbench.
- Safe bounded quota recovery, serialized auth refresh, complete multi-vehicle/HA entity reconciliation.
- All applicable historical entity/attribute/service/control contracts explained and verified; no fabricated telemetry or unknown safety state.
- Architecture, code, docs, generated inventories, tests and release gates aligned.
- Static code-complete acceptance and full CI before experimental publication; physical vehicle and rollback proof before stable.

Current b8 is not code-complete and no gate is flipped by this design documentation. All illustrative schemas, target module paths and performance targets need implementation and validation.
