# Runtime engineering workflow — b18 development

## Incident: all controls pending review
b17 Q8 diagnostics (2026-11-12) recorded remote refresh HTTP 200/backend_completed,
then window heating start HTTP 502/uncertain. All 20 controls reported pending_review
while cloud polling succeeded. The b17 global interlock was an overreaction to uncertain execution, not proof of
unsupported capabilities. The temporary-error policy below replaces it. No automatic
retry or invented physical confirmation. The original diagnostics are private.

## Runtime API experimentation
The Workbench must not require a rebuild for a new query variant. Identity queries
and JSON variables are editable and executable using the selected vehicle and
existing native GraphQL authorization. The bounded validator accepts a single
userVehicles read, VIN selection, orderBy and renderPictures mediaTypes, plus
ordinary field selections. Experiments remain separate from active bindings.
No raw credentials, arbitrary hosts, mutations or automatic physical actions.
The existing CARIAD/MBB read and command candidate workflows remain guarded.

Further work: persistent named request drafts, supported header profiles, reusable
sanitized definition export/import, explicit reviewed activation of identity routes,
and a common community contribution contract. Do not claim these are implemented
until tested. New API hosts/auth families require a reviewed executor; not a generic
credential-forwarding proxy. Physical commands require per-action consent,
journal, cooldown, verification and revision binding.


## Capability isolation
The temporary-error policy below governs routine uncertainty; only pending or
security-sensitive unresolved commands retain a capability-scoped review interlock.
Other capabilities remain usable subject to existing policy, cooldown and quota.
The bounded journal preserves outcomes without making ordinary history an interlock.
The single Workbench physical-test slot still requires review before another
Workbench test; unrelated normal commands remain usable.


## Local draft persistence
One private draft per existing identity template is stored in the vehicle profile.
Save local draft is independent of Submit; neither action changes the production
mapping. Reset template restores the built-in document in the editor; saving it
replaces the private draft. The draft persists across restarts. Named multi-draft
libraries and reviewed portable community import/export are still open.


## Temporary operational errors (supersedes permanent normal-command review)
Ordinary HA command failures do not remove a supported route or require manual
review. An uncertain HTTP 5xx/timeout is reported immediately, remains truthful
in history, and allows a new explicit request after 30 seconds (existing quota,
wake budget and engineering cooldown still apply). Routine controls stay visible;
an early retry gets a useful error. No automatic replay. Only unresolved access
and remote engine commands retain mandatory review due to their consequences.
The Workbench physical-test review remains proof for activation, not a routine
HA command prerequisite outside the tested capability.

## Engineering discipline
Follow the canonical [simplify-before-adding policy](V3_ARCHITECTURE_CLOSURE.md#mandatory-engineering-principle--simplify-before-adding). Reuse the existing operation, evidence and mapping owners before adding another layer. Keep runtime experimentation distinct from approved production mappings without duplicating the executor.

## Operation pattern consolidation — first audit findings

Apply the [80/20 operation rule](V3_ARCHITECTURE_CLOSURE.md#8020-rule--one-generic-operation-pattern). Current source inspection identified these concrete consolidation candidates (not implemented):

| Area | Current deviation | Preferred cleanup |
|---|---|---|
| Request rendering | `engine._operation_request` uses separate built-in path/body rendering and `DevelopmentProfile.preview_request` for custom routes | Reuse the existing typed renderer for equivalent definitions, retaining secret resolution at dispatch |
| Parameter contracts | `command_parameters._BINDABLE` is climate-only; charge mode and auxiliary duration validation are hardcoded in `command_payloads.build` | Declare standard types, ranges, enums and safe body templates in existing operation definitions; preserve secure binding restrictions |
| Response mapping | `attribute_runtime.observe_read_only` handles batch data; `StatusEngine._record_attribute_response` separately extracts, validates and writes custom-route observations | Reuse the same extraction, transformation, capture ordering and evidence contract; retain batch planning |
| GraphQL | Identity has a separate bounded query editor and native read executor | Share operation definition/result semantics, keep family-specific query validation and approved auth |
| Transformations | Existing `api_value_mappings.normalize_api_value` uses HA converters; command payload temperature conversion and other domain conversions are separate | Reuse declared conversions when semantics match; document true domain-specific calculations |
| Command execution | `CommandEngine.test_action` and `send_control` share dispatch but separately manage outcome/persistence | Use common lifecycle, with Workbench review as an explicit administrative step |
| Genuine exceptions | MBB security token, engine proof, settings-preserving PUTs, structured trips | Keep narrow reviewed handlers; extract common primitives only from proven multiple uses |

Baseline `d2b31e9`: catalog has 62 built-in operations; a validated generic/parameterized/exceptional classification of supported variants is still required before reporting an 80% coverage number. Do not claim that target has been achieved. No new renderer, workflow engine or transform language is authorized by this audit.

## Cleanup slice 1 — shared built-in/local request rendering

Built-in and local operation definitions now use the existing registry-backed
profile renderer. Secure markers stay unresolved in previews, and dispatch
retains exact existing credential and family checks. Built-in batch job commas
and the reviewed MBB US endpoint exception are preserved. Removed duplicated
immediate-parent capture timestamp extraction from Engine and StatusEngine;
ancestor capture extraction retains its separate semantics. Regression evidence:
existing template/security tests plus built-in preview parity. No release
intent, catalog activation policy, or frontend redesign in this slice.

## Cleanup slice 2 — shared observation commit

Batch and targeted read processing now share capture ordering and atomic value/evidence updates in `attribute_runtime.record_observation`. An older targeted sample can still be recorded as a route test but cannot overwrite canonical evidence while a newer vehicle reading is retained. Existing semantic filters and specialized structured normalizers remain unchanged; their consolidation is a subsequent slice. No additional runtime modules.

## Cleanup slice 3 — direct template editing

Four Workbench views remain. Existing read/command/new-attribute forms share a field/value renderer; nested definition fields are foldable. Selected backend route metadata seeds alternatives instead of unrelated defaults. Per-vehicle, per-template in-memory edits survive rerender and validation errors. Existing add/test/activate endpoints and physical consent remain unchanged. This slice does not yet unify identity query editing or command parameter schemas, nor replace the existing activation workflow. No new frontend framework or runtime module.

Direct read template editing now supports Save & test GET in one explicit action (save local definition, then test, never activate). New route selection uses the actual `saved`/`route` response contract. Existing physical controls still separate save from execution. Template details are expanded by default, with nested values foldable; scope is preserved when copying a command definition.

## Cleanup slice 4 — canonical attribute status

Discovery progress and detailed capability reports now use the same attribute-status calculation, including runtime-derived readings, freshness and invalid values. Persisted route outcomes remain distinct from current vehicle observations. Counts exclude local additions in historical-catalog progress; scope remains explicit. No new module or extra API call.

## Cleanup slice 5 — shared command parameter contracts

Charge mode, target SoC, auxiliary duration and CARIAD/MBB climate temperature use shared typed validators and the existing HA unit conversion mechanism. Workbench displays backend-provided parameter schemas as field/value inputs, not independent UI capability rules. Raw JSON remains for the exceptional heterogeneous settings update. Existing custom binding restrictions remain intact. No new modules.

## Cleanup slice 6 — shared command preparation and transport outcome

HA and Workbench reuse command preparation, including deferred OEM security proof after durable journal persistence. Both record initial HTTP outcomes using `CommandRecord.observe_http`; dashboard command rows no longer borrow HTTP status from the latest call to the same operation. Older stored records restore with unknown HTTP status. Manual physical verification and automatic HA readback remain distinct policies, not duplicated transport implementations.

## Cleanup slice 7 — shared response extraction and scalar mapping

Registry, historical batch mappings and targeted attribute routes now share ordered response-path extraction. Batch and targeted scalar normalization share type/unit checks, sentinel handling, empty/error-envelope rejection and size limits. False/zero and meaningful externalPower `unavailable` remain valid. Structured and legacy domain normalizers remain explicit exceptions. No new module or additional cloud call.

## Cleanup slice 8 — shared settings-preserving update

Charging and climate settings updates now share a single reviewed read/validate/patch implementation. The two endpoints retain their existing distinct preservation policies (charging rejects unknown fields; climate preserves unrelated reported fields). Charging profiles and climate start with settings retain their specific domain handlers. No arbitrary PUT or generic workflow language added.

## Cleanup slice 9 — declarative parameterized charge-mode operation

The reviewed charge-mode PUT now declares its enum, binding and body in the existing operation catalog and uses the common renderer. Its code-specific payload branch is removed. Reviewed PUT aliases inherit the exact original template, not editable replacement bodies; existing custom input restrictions remain. Operation revisions change when definitions change, so prior local physical evidence is not automatically transferred.

## Cleanup slice 10 — remove obsolete climate-pilot frontend workflow

Removed the unused climate-only route wizard, hidden action handlers and redundant `routes` WebSocket call from the frontend. Current attribute, control and identity workflows remain. The four views are retained, and pending action state is obtained from the current status/selected control endpoints. Existing backend compatibility endpoints are not removed in this slice. Tests exercise the actual read candidate workflow rather than unreachable pilot UI.

## Cleanup slice 11 — remove stale UI contract and make repeated experiments practical

The release contract now checks the actual attribute-save frontend path rather than the retired climate wizard. Removed redundant attribute-status initialization (canonical evidence computes it once). Alternative templates propose an attribute/action-specific unused identifier among the loaded variants, and refresh preserves the selected route instead of reverting to the active route. Backend uniqueness and activation validation remain authoritative; variants are still immutable.

## Cleanup slice 12 — common rendering and physical dispatch

Attribute routes now reuse the existing validated definition renderer, retaining required job selection. HA and Workbench now share one post-journal physical dispatch and initial HTTP/API-evidence path; each still applies its distinct confirmation policy. A confirmation failure does not overwrite the original HTTP observation with a transport failure. No new executor or workflow framework.

## Audit 02 — isolate read experiments and preserve user decisions

Manual attribute tests record candidate evidence only. Activation persists the selected mapping; normal polling publishes observations. A transient failure does not discard a selected route on restart. Explicit disabled data mappings remain disabled across discovery/restart; shared telemetry may still be read for other functions. Resume automatic discovery or activate a verified candidate explicitly. Control re-enable clears user disablement without creating proof or sending commands. No release authorization change.

## Audit 02 — remove unproven automatic identity research

Normal inventory uses the canonical original GraphQL request and validated last-known metadata. Removed automatic garage/after-garage/extended/modern recovery chain from discovery. Those definitions remain explicit Workbench research; successful manual comparison does not update production identity. Optional vehicle image delivery is a distinct product feature and retains its bounded read. Manufacturer model remains unresolved on the target vehicle; no claim of identity acceptance.

## Audit 02 — retire pilot administration endpoints

Removed obsolete `routes`, `test`, `save_candidate` and `disable` WebSocket handlers and the separate auto-activating status test facade. Read variants use attribute add/test/save/activate/disable; controls use the existing generic control workflow. New capability-level GET variants cannot be created through the old control route API. Stored legacy profile selections remain readable for compatibility until their explicit migration; no user data silently removed. Current architecture baseline and engineering lifecycle updated; software release gates remain closed.

## Audit 02 — complete experiment isolation and disabled inventory

Manual quick/full API-family scans record evidence without publishing live attributes, activating bindings or updating trip history. Disabled inventory is accessible across capability and API-family filters, including controls without candidates. The afterGarage two-request comparison is retired as an executable template; its historical identifier remains valid provenance and cannot be selected for a new test. A stored afterGarage draft migrates to the identical canonical inventory template unless an explicit canonical draft already exists, in which case the latter wins.

## Audit 02 — remaining acceptance work

This remediation does not establish zero technical debt. Remaining work includes removing the runtime distinctions based on the single-capability pilot fixture, consolidating climate reported state with canonical attribute observations, resolving duplicate operation/evidence identifiers, completing template-driven authoring and portable draft/release lifecycle, and validating actual target-vehicle identity, HA lifecycle and rollback. Retain security checks, stable entity identifiers, reviewed legacy support and historical evidence. Do not publish or merge on the basis of passing unit tests alone.
