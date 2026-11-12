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
