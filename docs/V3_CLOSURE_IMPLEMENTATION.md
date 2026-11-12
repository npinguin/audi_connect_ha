# Architecture closure — implementation progress

Current development work (2026-11-12) is not a release or parity sign-off.

Implemented:
- Account auth refresh lock, serialized transport and bounded quota recovery.
- Persistent normal command context before dispatch, restart uncertainty and cooldown, explicit review.
- Separate StatusEngine and CommandEngine composed by V3Engine; existing public HA service contracts retained.
- Generic non-climate status evidence, scheduling, mapping of scalar capability observations and restore; dynamic HA projection on all nine platforms.
- Serialized profile writes, durable CARIAD request IDs, post-command readback for known stateful actions, and journal persistence before special engine proof preparation.
- Pure automatic fast control resolution with catalog-matched versus versioned local evidence, user-disable/impairment/security checks, no actuator calls during discovery; one persisted evidence snapshot per poll.
- Machine-readable current module ownership; synthetic regression tests.
- Machine-readable V2 upstream delta inventory and a blob-integrity regression gate (review required, not semantic parity).
- Removed obsolete V3Runtime, inherited coordinator and first climate implementation/catalog from production. Minimal catalog remains test-only; persisted runtime selector stays unchanged.

Still open:
- Arbitrary new control semantics remain intentionally closed until a reviewed handler exists; local typed read-only attributes, HA projection and reviewed parameterized/PUT templates are implemented. Historical V2 source mappings remain for compatibility.
- Shared bounded journal is implemented; physical readback covers known stateful actions and cannot prove all transient actions.
- Full HA integration acceptance and physical rollback. Context migration, inventory removal and return are implemented.
- Complete semantic review of retained V2 deviations, CI type/coverage gates and actual vehicle/recorder/rollback proof.
- Review actual catalog eligibility across supported vehicle families. Catalog match is not physical proof.

Do not mark static parity or release gates complete.

- Vehicle inventory reconciliation retains object/entity identity, blocks excluded or repeatedly missing VINs, and restores them on rediscovery. Empty/malformed responses do not revoke existing vehicles. Context-change migration now invalidates old evidence and preserves unresolved commands; physical acceptance remains open.

## Post-b8 V2 parity work

Removed the dormant V2 probe implementation (account methods, service adapter, diagnostic report and standalone probe module). V3 family-read tests cover the supported engineering path. Refreshed the machine-readable operation inventory directly from the active catalog; added exact inventory regression and V2/V3 differential tests. No parity flag is promoted.

### Parameterized controls

Verified local CARIAD climate-start settings templates can map a declared typed variable to the canonical temperature parameter, with range validation at every invocation. PUT aliases are configurable only around the existing code-owned handler, exact approved endpoint and no replacement body. Generic admin route save/select/disable accepts capability and action. Other dynamic templates remain engineering-only until a semantic parameter contract is implemented; this is not arbitrary raw PUT support.

### Shared execution history and context migration

A bounded 50-record private command journal now records both HA and Workbench executions with origin, operation revision and separate backend/physical outcomes; old last-command records remain readable. The guided discovery review model is retained as the evidence UI, not a separate dispatcher. Vehicle context changes invalidate route bindings/evidence and in-memory observations while preserving definitions, user-disabled controls, history and pending uncertainty. Older-version HACS downgrade after adding new custom fields still requires backup/restore; runtime V2 fallback is distinct.

### Post-b8 declarative local attributes and ownership

The admin Workbench can define a new vehicle-local read-only attribute and capability presentation group with a namespaced identifier, typed value, HA metadata and GET response/capture mappings. A draft is not an HA entity; a successful test and explicit activation are required. Selected reads are deduplicated and rotated within the four-route poll budget. This is not arbitrary new control authorization. Historical V2 identity and the 59-operation global catalog are unchanged. Ownership completeness and the core domain-to-composition import boundary now have executable regression checks. Full dependency-cycle, typing/coverage and physical parity acceptance remain separate gates.

### HA binary metadata parity

All 23 V2 binary sensor names, device classes, icons and categories are captured independently and compared against actual V2 descriptions in the HA projection tests. The baseline distinguishes raw fixture values, metadata and physical Q8 evidence. Legacy timer payloads and CARIAD reset-history semantics remain unverified; do not fabricate data or promote static/full parity flags.
