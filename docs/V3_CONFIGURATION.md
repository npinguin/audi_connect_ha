# Audi Connect V3 — configuration and discovery

**Current baseline:** 3.0.0b9 is explicitly authorized as a supervised experimental HACS test prerelease, not a code-complete or stable release. Back up HA, select this beta explicitly in HACS, restart, and keep V2 as fallback. See the [b9 release notes](V3_RELEASE_NOTES_3.0.0b9.md). Older beta installation instructions are historical and should not be used as current guidance.

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
