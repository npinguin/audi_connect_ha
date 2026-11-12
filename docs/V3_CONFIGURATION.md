# Audi Connect V3 — configuration and discovery

**Current baseline:** 3.0.0b11 is explicitly authorized as a supervised experimental HACS test prerelease, not a code-complete or stable release. Back up HA, select this beta explicitly in HACS, restart, and keep V2 as fallback. See the [b11 release notes](V3_RELEASE_NOTES_3.0.0b11.md). Older beta installation instructions are historical and should not be used as current guidance.

## Shared setup and rollback

Keep the existing Audi Connect config entry and vehicle device; never create a second account merely for V3 or delete the entity registry. Back up HA before an authorized beta test. Options select the runtime (existing stored option `v3_climate` identifies V3; default V2). Switching reloads the integration. Keep credentials, scan settings, V2 preferences and local dealer metadata. Existing entity IDs, user-disabled states and stored V3 profiles must survive V2↔V3. All nine HA platforms have independent V3 projection; actual availability depends on vehicle evidence and supported routes.

## Current engineering behavior

The optional administrator-only V3 Development Workbench is off by default. Enable it only in V3 for engineering experiments. Select the current vehicle, capability, attribute or control. GET tests are read-only; choose a single exact control route, provide required parameters and approve that action. Review the physical result before activating an experimental route. Saving a draft is not activation. Never store a real S-PIN in custom configuration or UI history. Unknown or uncertain results do not authorize alternative automatic actions.

Current limitations: some status/profile operations remain climate-specific; custom attribute routes are limited to known attributes and CARIAD GET; custom parameterized command activation and custom PUT templates are incomplete. Some reviewed historical default routes are already made available by capability evidence; they are not proof of local physical success. Full static/live parity and rollback remain open.

## Target: automatic fast discovery for end users

Normal users should not configure API routes, select candidates or manually test control entities. After login, the integration automatically matches supported capabilities and commands using the normal read pass, reviewed catalog rules and compatible saved vehicle bindings. Eligible known controls are exposed automatically as native HA entities. Unsupported or inconclusive controls remain unavailable with a reason. Startup and discovery never actuate the vehicle or automatically wake it; an intentional HA action invokes the command engine.

The Workbench remains optional for engineers and exceptional unsupported cases. Review/validation occurs during engineering, not as a prerequisite for every end user's setup. See [ADR 002](V3_ADR_002_FAST_DISCOVERY.md) for evidence precedence, safe activation and acceptance tests, and [Architecture Closure](V3_ARCHITECTURE_CLOSURE.md) for the implementation plan.

## Audi Engineering Dashboard

The optional admin-only V3 Development Workbench is presented as **Audi Engineering Dashboard** (same sidebar URL and configuration option). Overview summarizes vehicle data, controls and next actions. Capabilities scopes functions to one domain, with separate data/control views and S-PIN filters. Configure & test focuses on one function, with explicit approval, physical review and activation preserved. API evidence contains the detailed operation matrix, historical inventory, response previews and read-only scan. Changing vehicle clears selected actions and evidence before loading the new vehicle. No dashboard navigation sends vehicle commands.

### Local engineering response inspection

Select a route and choose Inspect actual JSON response. Detailed decoded response bodies (GET and command results) are masked using template placeholders `{VIN}`, `{SPIN}`, `{SECRET}`, `{LOCATION}`, `{PERSONAL}`, `{ID}`. This admin-only view reads bounded RAM evidence from existing calls; no additional Audi request and no disk persistence. After restart or eviction, rerun only a safe read if needed. Do not repeat a physical action for debug evidence. Diagnostics remain restricted and command bodies withheld. Response limits and masking are explicit; the engineering view is not a public export.

### Read-only coverage and execution history

The dashboard shows the actual masked request and response immediately after a test and when browsing recorded executions. Local history is bounded to 24 executions; latest per-route detail is bounded to 32. No headers or credentials are exposed, and detailed evidence is not persisted. Older persisted evidence is labeled restricted. Full scan explicitly tests distinct applicable fixed catalog GET routes in resumable batches of up to 12 calls with a quota reserve of 12. Unmapped jobs are included in automatic bounded follow-ups. Context-incompatible, custom and parameterized routes are excluded with a reason; no automatic mutation or activation.

### Climate everyday controls

The native climate entity remains primary for state and target settings. Start climate (car settings) and Stop climate are explicit non-diagnostic buttons, using their existing unique IDs and individually activated routes. They do not depend on fresh climate telemetry; the climate state stays unknown when stale. The compatibility switch remains hidden by default. No command is sent by discovery or entity setup.
