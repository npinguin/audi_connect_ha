# Runtime engineering workflow — b18 development

## Incident: all controls pending review
b17 Q8 diagnostics (2026-11-12) recorded remote refresh HTTP 200/backend_completed,
then window heating start HTTP 502/uncertain. All 20 controls reported pending_review
while cloud polling succeeded. The command interlock is intentional: a 502 does not
prove a mutation failed. Acknowledge only after inspecting the actual vehicle, via
the Workbench review banner. No retry or invented physical confirmation. The banner
now names the blocking operation and state; the decision reason distinguishes
in-flight, uncertain and engineering review. The original diagnostics are private.

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
Uncertain normal commands block only their capability. Other capabilities may
operate subject to existing policy, short anti-flood cooldown and quota. Every
unresolved normal command remains in the journal across unrelated actions and
restart, and can be acknowledged by ID after inspection. No retry or automatic
authorization. The single Workbench physical-test slot still requires review
before starting another Workbench test; normal unrelated commands remain usable.


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
