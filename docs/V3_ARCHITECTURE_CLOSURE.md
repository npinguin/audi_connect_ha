# Audi Connect V3 — Final Architecture Closure

**Status:** current engineering direction; closure work packages remain open. Canonical branch: `feature/v3-clean-discovery` (draft PR #22). Audit 02 baseline: `ac89f6581b06fae96defd5e0858aa3b50e7ec43c`. Subsequent remediation commits and CI evidence are tracked in the PR. Last explicitly authorized experimental publication remains b17. Do not create a V4, parallel runtime or permanent feature branches. No beta/stable publication before the relevant gates.

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

## Mandatory engineering principle — simplify before adding

V3 is entering stabilization and cleanup. Avoid additive "lasagna" architecture:
a bug, missing capability or ambiguous API result is not justification for a new
layer, framework, fallback, state model or defensive interlock.

Every change must first inspect the existing owner, contract and implementation.
Prefer, in order: delete obsolete behavior; consolidate duplicated behavior;
correct or reuse the existing implementation; extend the canonical contract;
add a new component only if none of those meets a demonstrated requirement.

- One canonical source of truth per fact and one owner per responsibility.
  HA, Workbench and diagnostics are projections of the same evidence, not
  independent capability/state models.
- Prefer native Home Assistant entities and semantics. Avoid parallel controls
  and redundant sensors unless compatibility or distinct user value is proven.
  Preserve stable entity IDs, user-disabled choices and V2 rollback; retire
  integration-disabled legacy entities only with a documented migration.
- Separate capability support from execution outcomes. Report errors clearly,
  use bounded temporary cooldowns and permit explicit retries for ordinary
  transient failures. Do not permanently disable a capability on speculation.
  Keep proven security, quota, consent and physical-action safeguards; never
  fabricate success, replay a mutation automatically or weaken an established
  authorization boundary to reduce code.
- Prefer declarative, validated runtime definitions and the existing Workbench
  for new query/mapping variants; no build/deploy for each ordinary experiment.
  Do not invent a generic framework for a single exception.
- Refactor in the same change when reasonably scoped. Remove obsolete paths,
  duplicated mappings, dead configuration, redundant tests and superseded
  documentation after proving the replacement. No permanent fallback chains
  or parallel pilot implementations.
- Keep tests focused on user behavior, contracts and actual failure modes.
  Replace obsolete assertions rather than preserving accidental complexity.
  Do not equate more tests, more modules or less code with correctness.

### 80/20 rule — one generic operation pattern

Aim for at least 80% of ordinary API operation variants to be expressible as
validated declarative definitions on existing owners, with no new Python or
JavaScript handler and no rebuild for a local experiment. This is a design
target, not a measured current result, mandatory numeric release threshold,
or a reason to weaken a safety boundary. The unit of measurement is an actual
supported operation variant, not a line of code or an individual response field.
Classify operations as generic, parameterized generic, or exceptional; count
the first two together and report the denominator. Do not inflate coverage
with aliases or duplicate historical references.

The standard operation definition must describe the same concepts for built-in
and community/local operations, using the existing catalog/registry and typed
runtime definitions rather than a parallel framework:

| Contract | Generic pattern |
|---|---|
| Identity and context | Stable operation ID, capability/action, API family, applicability |
| Request | Method, approved relative path, query/document, typed parameters, body template |
| Execution | Shared template validation/rendering, family-specific auth/transport, quota and observation |
| Response | HTTP and API-level result, extraction paths, optional capture path, schema and type |
| Mapping | Canonical attribute IDs, explicit source/target units, reusable enum/value transforms, null/sentinel rules |
| Command | Same lifecycle for HA and Workbench; explicit consent where required, command ID, result, optional readback |
| Evidence | Operation revision, source, timestamp, outcome; shared diagnostics and HA projection |

A GraphQL POST query is a read operation, not an actuator command: classify by
intent, not HTTP verb. Batch reads may populate many attributes from one request.
Built-in and local definitions must use the same validation, rendering, mapping
and execution machinery wherever their semantics are equivalent. Workbench
draft/test/activation is an administrative workflow around that machinery, not
a second implementation. Use declarative type/range/enum constraints, JSON path
extraction, reusable transforms and existing HA unit converters. Do not add
arbitrary scripts, expression evaluators, arbitrary URLs or credential fields.

Exceptions require an observed protocol or domain constraint, a named existing
owner and focused regression evidence. Examples: OEM multi-step security proof,
legacy security-token exchange, destructive PUT read-modify-write preservation,
and complex structured arrays or trip reconciliation when a simple mapping is
not sufficient. A different field name, unit, endpoint, parameter, standard body,
or enum is not by itself an exception. A reusable safe read-modify-write pattern
may become generic once multiple real uses establish the common contract; do
not invent a general workflow language. Family executors retain auth/host
security ownership. Every exception reuses the common lifecycle, transport,
evidence and result handling unless a concrete reason prevents it.

Review new operation variants against this pattern first. Existing deviations
are cleanup candidates, not permission to add more. Preserve semantic validation,
credential isolation, physical safeguards and current release authorization.

### Workbench UX — four views, template-driven direct editing

Keep Overview (health and findings), Capabilities (functional coverage and
entity links), Configure & Test (operation editing and execution), API Log
(request/response evidence). They are complementary navigation views, not a
mandatory sequential wizard.

In Configure & Test, select an operation and edit field/value boxes on the
same screen. Use actual backend template definitions, not invented defaults
or a separate frontend catalog. Show simple fields directly; fold nested
JSON, optional parameters, mapping details and technical evidence. Execute
and inspect results in place, without a mandatory read-only confirmation.

Frontend checks are basic syntax, types and required fields; existing backend
validators remain authoritative for semantics, applicability, security and
activation. Preserve edits on validation errors. Drafts remain distinct from
active definitions. Saving must never actuate the vehicle; explicit physical
command consent and review remain where required. No fifth view, new UI
framework, or bespoke editor per ordinary operation.

### Change review / definition of done

For each PR or engineering change, record in the existing PR description or
review notes (a few sentences are sufficient):

1. What existing owner/contract was reused, corrected or consolidated?
2. What obsolete or duplicated behavior was removed, or why is none relevant?
3. If adding a layer, fallback, model, entity or persistent state: what observed
   requirement cannot be satisfied by the current owner/contract? What is the
   retirement condition for any transitional mechanism?
4. For operation changes, is the variant generic/parameterized or exceptional?
   If exceptional, document the real constraint and existing owner.
5. Which existing behavior, HA compatibility, failure recovery and release
   constraints were validated? What remains unproven?

Unjustified parallel implementations, duplicate facts, permanent workaround
layers and speculative feature lockouts are review blockers. A small focused
change may simply state that no additional complexity or cleanup is needed.
Do not create a separate approval process, arbitrary LOC target or generic
cleanup framework. Review is risk-based and part of the existing delivery flow.

## Governance and quality gates

Current machine-readable artifacts: `governance/OWNERSHIP.json`, `governance/V2_UPSTREAM_DELTA.json` and `governance/V3_COMPLETENESS_GATE.json`. Reuse these owners and existing CI; no separate governance framework. Dependency direction and complete cycle validation remain open. Enforce import/AST dependency direction, no cycles, lint/format, typed public contracts, risk-based coverage, HA lifecycle tests, generated parity/catalog inventories and no unexplained V2 drift. Exact-SHA pytest, Workbench, hassfest and HACS remain required. Do not assert coverage from source strings alone.

## Definition of Done

- Exactly one runtime per config entry; modular ownership and no old V3 pilot.
- V2 near-upstream behavior with all deviations explicitly governed.
- New simple capability, attribute and approved GET/POST/PUT configuration requires no generic engine change.
- One status resolver and one persistent command lifecycle, including typed persistent bindings and restart recovery.
- Manual engineering discovery generates reviewed reusable compatibility evidence; end-user fast discovery automatically exposes applicable known controls without physical actions or required Workbench.
- Safe bounded quota recovery, serialized auth refresh, complete multi-vehicle/HA entity reconciliation.
- All applicable historical entity/attribute/service/control contracts explained and verified; no fabricated telemetry or unknown safety state.
- Architecture, code, docs, generated inventories, tests and release gates aligned.
- Simplify-before-adding review satisfied; replacement paths and migration validated, unjustified duplication removed.
- Static code-complete acceptance and full CI before experimental publication; physical vehicle and rollback proof before stable.

The current development branch is not accepted as code-complete and no gate is flipped by this design documentation. All illustrative schemas, target module paths and performance targets need implementation and validation.
