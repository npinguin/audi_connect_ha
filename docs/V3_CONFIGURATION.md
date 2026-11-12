# Audi Connect V3 — configuration and discovery

**Current baseline:** 3.0.0b12 is explicitly authorized as a supervised experimental HACS test prerelease, not a code-complete or stable release. Back up HA, select this beta explicitly in HACS, restart, and keep V2 as fallback. See the [b12 release notes](V3_RELEASE_NOTES_3.0.0b12.md). Older beta installation instructions are historical and should not be used as current guidance.

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

### Native vehicle control pattern

Cabin climate is one native climate entity, preserving its original identity. Mode Heat/Cool sends the activated bodyless start by default; Off sends stop. A separately selected target is staged without starting the vehicle, and an explicit start uses the settings-bearing route. A combined temperature/mode action is explicit. Unknown/stale or pre-command captures remain unknown. No invented default target or assumed physical state. The compatibility switch is disabled by default (re-enable manually if an existing automation needs it); old pilot Start/Stop buttons are retired without deleting registry records. V2 is unchanged. Central locking remains a single native lock. Charging and window heating retain explicit buttons pending reliable state mapping; never manufacture a switch state from command acceptance.

A dispatched climate setpoint is distinguished from the last reported vehicle target. A newer vehicle capture supersedes the requested setpoint; a rejected command does not change the displayed target. Disabling the temperature-bearing route must not block ordinary climate on via the stored-settings route.

The three existing modern trip endpoints are in the mobility catalog and use the same normalizer in regular polling and full read-only scans. Ordinary parking/trip results now participate in masked engineering evidence without extra calls. Legacy MBB trip-date queries remain separate pending template consolidation; no location values are exported in diagnostics.

### Product names

All built-in entity names are functional, independent of API family and migration status. Source and compatibility details remain engineering metadata. Registry migration updates only integration-owned original labels, including unavailable records; user names, unique IDs and entity IDs are preserved. Hidden compatibility records remain available for existing automations and may still appear with Home Assistant's own Hidden indicator in administrative views. V2 implementation remains untouched.

### Development after b12: operational controls and model

Charging and Window heating use one native switch when both semantic command routes and a recognized vehicle status have been observed. Unknown states are not off; stale data is not live. Existing buttons are preserved for automation compatibility and hidden by default only when the switch has supporting evidence. Window status uses the separate front/rear status array, not the climate preference or legacy mirror heating. Manufacturer model and model year are read from inventory, independent of nickname. Public upstream examples document the window status shape and charging notReadyForCharging; actual Q8 on/off values still need verification in b12. No b13 release authorized.

Inventory debugging: select GraphQL under API evidence to see the original decoded row of the selected vehicle and actual fixed read-only query, without other account vehicles. Its transport uses POST but is explicitly classified as read-only inventory, not a physical command. Restricted exported evidence does not contain the row.

### Accepted command projection

Stateful HA controls immediately project accepted commands while retaining reported telemetry and physical evidence separately. New valid post-command captures override the projection, even if they disagree. A 30-minute bound prevents an indefinitely assumed state; rejected or uncertain commands are not optimistic, and no commands replay after restart. Climate ON displays Heat/Cool without inventing heating versus cooling. Charging, window heating, auxiliary heating, supported boolean climate settings, global charge target and preferred mode share the projection. Locks use native locking/unlocking pending states, not assumed locked/unlocked. An explicit stop immediately after an accepted start bypasses only the normal cooldown for that same function; all other route, authorization, uncertain-command and engineering gates remain. Direct timestamped CARIAD telemetry in a reviewed response envelope is normalized before projecting. Profile-specific settings require scoped readback and are not guessed. No b13 release.

Modern trip data now retains OEM total electric energy (kWh) and fuel volume (L) as normalized trip attributes. The observed unsuffixed electric consumption average is exposed in kWh/100km only when corroborated by explicit energy total and distance. Existing timestamp entities and trip IDs are unchanged; these trip totals are not lifetime energy counters or charging-meter measurements.

### Native trip measurements (development)

Last trip and long-term trip expose distance, duration, average speed, average fuel/electric consumption and actual total liters/kWh as native sensors when present. The timestamp sensors keep all normalized attributes. No extra requests, no invented zeroes, no per-trip total-increasing meter and no claim that long-term trip totals are lifetime counters. Recorder can record state transitions prospectively. The normalized historical short-term array is retained in local session memory (up to 1000 distinct trips), sorted and deduplicated with the last-trip endpoint. Long-term aggregates are never mixed into history. Durable historical storage, pagination and historical Recorder import are not implemented.
