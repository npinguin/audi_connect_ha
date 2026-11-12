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

### Entity and refresh rationalisation after b8 diagnostics

Retire source-proven V3-only climate capability and V3 cloud polling sensors with an exact ID migration, preserving registry/history and user-disabled entries. One account cloud-refresh button retains the first VIN's historical unique ID; duplicate per-VIN controls are retired, vehicle refresh is explicitly named and wake is opt-in for new registry entries. Cloud health derives from real poll success, not local listener notification. A valid stale timestamp does not itself trigger an alternate GET. Restore 49 explicit V2 sensor icons; retain intentional V3 category changes. Model year is read from trusted GraphQL core metadata; remote engine control fails closed without model or drivetrain. Old Start/Stop climate button identities require exact registry evidence; no name-based deletion.


### Product rationalisation — Q8 b8 audit

- Product identity contract: `custom_components/audiconnect/v3/product_entities.json` defines the 109 historical V2 identities plus three deliberate V3 extensions (account cloud refresh, climate quick switch, last trip). Vehicle-local validated custom attributes are explicit exceptions. Raw fields remain in the API catalogue/Workbench and may be used by commands without automatically becoming duplicate HA entities.
- 15 raw-only historical V3 sensor keys and two pilot diagnostic keys are retired by exact integration-owned identity; registry records, recorder history and user-disabled choices remain. No guessed climate-button identifier is migrated. The next diagnostics export includes redacted registry/projection comparison and unknown-key fingerprints.
- Cloud and vehicle refresh are separate contracts. Default post-command follow-up is read-only. Opt-in V2 vehicle refresh runs only after a backend-completed/verified command, with its own linked journal record, safety checks and shared wake budget. Unconfirmed/failed refresh never emits a successful completion event.
- Active charge mode and preferred charge mode are distinct sources; the latter drives the select, not the active-mode sensor. Equivalent historical aliases are resolved from the latest real capture rather than dictionary insertion order. Existing sensor metadata and identity are preserved.
- Restored quota values are last-known display data, not current headers or transport budget. Source and currentness are explicit attributes.
- Native climate sends a temperature-bearing start when supported; the quick switch intentionally uses stored car settings. Both use the same command journal and verified route policy. Physical parity and migration acceptance remain open.

## b9 — Q8 semantic and evidence audit

Numeric contracts reject booleans, invalid percentage ranges and invalid negative remaining durations; newer invalid captures are not overwritten by older cached data. Oil level boolean uses the existing warning binary sensor. V3 metadata correction and existing HA identities are retained. The Workbench projects capability, operation, command, attribute and HA registry evidence; bounded redacted GET field inventories identify review candidates without enabling unreviewed controls or extra requests. Historical references, HTTP acceptance and physical verification remain separate. Model-specific field semantics and actual Q8 oil warning polarity require vehicle evidence. No parity flags promoted.

## b10 — product entity rationalisation and Audi Engineering Dashboard

Vehicle binary properties are functional sensors, not diagnostics. Compatibility entities remain available for existing automations and are hidden by default when redundant evidence is present. Existing registry categories and integration-owned visibility changes are tracked for V2 rollback. Native climate is primary; charging controls require read/write eligibility. No physical acceptance claim.

## b11 — maintainability and capture quality

Native category policy and migration resolve shared product metadata. Behavioral projection and registry tests replace brittle implementation checks. Observed-job freshness is conservative while historical age retains newest-capture meaning. Bounded response inventory declares truncation and timestamps are metadata, not missing sensors. Legacy observation schemas remain readable. Physical acceptance remains open.
