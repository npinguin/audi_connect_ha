# Audi Connect V3 — user and engineering guide

**Configure → Discover → Use.** V3 is experimental and opt-in within Audi Connect. V2 remains the default and fallback. Keep one account, one config entry and the existing HA devices and entity IDs.

This guide describes the B41 development candidate. B40 is the preceding published test release; B41 is not yet a published or stable release. For exact release evidence and open gates, see [feature closure](V3_FEATURE_CLOSURE.md).

## User guide

### Installation and rollback

Follow the [main README](../readme.md) for installation and sign-in. Use a published, pinned HACS candidate containing V3; a GitHub review branch is not a published release. Back up Home Assistant before upgrading. In **Settings → Devices & services → Audi Connect → Configure**, select the experimental V3 runtime if available. Keep the normal scan interval (minimum 15 minutes). Leave the optional engineering Workbench and EU Data Act disabled unless needed.

V3 enumerates vehicles during setup; the V2-only startup update preference is retained for rollback. To revert, select V2 in the same entry and reload. Do not delete the integration or the registry to resolve a temporary data problem. Retain device IDs, entity IDs, user preferences and trip history. Verify automations after any runtime change.

### Data and freshness

Audi's cloud can be reachable while a parked vehicle has not sent new data. A cloud refresh is not proof of a new vehicle capture. No automatic wake on every poll.

| State | Meaning |
| --- | --- |
| Fresh | Valid measurement with a sufficiently recent vehicle capture. |
| Last known | Historical observation; check its capture time. Not confirmation of current state. |
| Unknown | No reliable current value. A historical value may still be available in attributes. |
| Unavailable | The entity or source cannot currently provide a usable value. Check the reason. |
| Not applicable | The underlying condition does not apply, e.g. charging ETA when explicitly not charging. Never interpret a missing ETA as zero minutes. |

Latest vehicle data age refers to the newest usable vehicle measurement, not the cloud receipt or oldest measurement. Oldest observed age and per-job ages remain available in attributes and the Workbench. Check the specific entity's capture time for automations. Data Act delivery may be fresh while the underlying capture is old. The tracker shows last parked position, not live GPS; movement without reliable vehicle capture stays unknown.

A previously registered, mapped read-only sensor is offered again on reload even if its current OEM value is absent. Its identity does not establish current availability or new vehicle support. Explicitly retired identities such as the redundant V3 Charging ready sensor remain retired; no registry deletion is required.

### Native controls

Use the HA vehicle device page for ordinary actions. Routes and features depend on the vehicle, auth context and verified capabilities. Missing controls are not permission to try a different API.

- Charging and window-heating switches in B41 no longer claim physical On/Off from a pending command. While the outcome is unconfirmed and no new valid readback exists, the switch can be Unknown; inspect last reported state and capture time. A newer valid contrary reading remains the actual reported state.
- Lock/unlock may show a bounded locking/unlocking transition, not a fabricated locked/unlocked state. Other supported comfort controls can expose explicitly marked optimistic feedback. Check requested state, command status, source and actual vehicle readback.
- HTTP 2xx means the backend accepted a request, not that the vehicle executed it. A timeout or mismatch is not proof of physical success or failure. Never automatically replay an uncertain command.
- Climate has separate read target, stored-settings start, temperature-bearing start, independent settings update and stop operations. The configured temperature can be readable even when no temperature-write route works. Temperature adjustment requires an enabled applicable write route selected by the resolver. A reviewed catalog match is not the same as local physical verification; an alternative route must be verified before activation. There is no model-specific assumption that Q5 or Q8 supports a particular route.

### Optional EU Data Act

Obtain an authorized continuous request in Audi's official portal. In V3 options, select Manage EU Data Act; enter portal credentials locally when required. The wizard and vehicle diagnostic show delivery status independently from native Audi health. Keep current connection does not reauthenticate.

Connected means a delivered or acknowledged unchanged dataset, not fresh vehicle data. Awaiting data means no confirmed delivery; subscription unavailable or access denied means check the portal request; authorization required means check credentials; rate limited means allow automatic recovery. Disconnect removes local optional credentials and observations without changing native Audi login or the portal request. Data Act is read-only; it never authorizes or confirms commands.

## Engineering Workbench

Enable the optional V3 Development Workbench in integration options as an HA administrator. Open **Audi Engineering Dashboard**, select the account and vehicle. Ordinary HA use does not require the Workbench.

- **Overview**: current findings, health and vehicle capture.
- **Capabilities**: compare source mappings, actual observations, supported actions and their HA entities.
- **Configure & test**: inspect an individual API route, its parameters and evidence; explicitly test or activate reviewed mappings.
- **API Log**: inspect bounded local request/response evidence and read-only scans.
- **End-user validation**: Guided walks eligible unverified actions; Expert selective lets you choose a capability or one action, including retesting eligible verified actions. Both use the same reviewed definitions, parameters and physical confirmation.

### Test a specific climate function

1. Safely park the vehicle, select it in the Workbench and open **End-user validation → Expert selective**. Filter by Climate.
2. To test stored settings, start with climate off; select Start cabin climate and confirm whether it really starts.
3. Stop climate, then select Start climate with temperature. Enter a different target temperature in °C. Verify both actual start and the requested target.
4. To test Change climate target temperature independently, start with climate off; choose a different target and verify it changes without starting climate.
5. Confirm Worked on vehicle or Did not work on vehicle for the actual outcome. If unsure, keep the test pending and inspect the car; do not replay it. Restore the vehicle to a safe state before the next test.
6. Check the native HA climate entity after validation. A successfully verified route is stored for that vehicle; failure on another vehicle does not authorize or disable this one.

The same physical instructions appear in Guided. A reviewed equivalent route may be tried after definitive rejection under the existing consent and quota rules; never auto-send a different semantic action. For a published B40 build, use Capabilities → Climate → Vehicle controls → Inspect & test for parameterized operations instead.

### Report a problem safely

Include the exact integration/HA version, vehicle model/year/powertrain and market (if known), action, local timestamp with time zone, expected versus actual outcome, and myAudi/physical evidence if relevant. Compare B35/B40/B41 only when the conditions and operation are known.

Download integration diagnostics from **Settings → Devices & services → Audi Connect → three-dot menu → Download diagnostics**. The integration's own data is designed to exclude credentials, tokens, VINs, coordinates, raw payloads and private trip values. The surrounding HA export can contain unrelated system or integration information: review it and share only the sanitized Audi Connect data section. Attach a ZIP if GitHub refuses the JSON. Do not share complete HA logs, raw responses, OAuth callback URLs or secrets.

Diagnostics are read-only and do not wake the vehicle. They distinguish transport requests, coordinator attempts, cloud reachability, vehicle captures, source coverage, registry projections and structural command evidence. They are not a full request timeline. Unknown quota is neither zero nor unlimited.

## Engineer and maintainer

Use the [architecture and ownership contract](V3_ARCHITECTURE_CLOSURE.md), [feature closure](V3_FEATURE_CLOSURE.md) and the existing catalog. The capability control in `full_catalog.json` owns reviewed discovery metadata: order, label, physical instructions and allowed parameter names. The shared `parameter_schema` supplies types and limits; the resolver and command lifecycle enforce vehicle applicability, consent and verification. Frontend and backend consume the same candidates. Extend a reviewed existing operation through catalog metadata plus regression tests; new semantics still require reviewed execution and verification support. Do not add a second catalog, poller, auth owner, entity store or command framework.

New native command-response observations use the same status writer as polling only when their own valid capture is newer than dispatch; HTTP acceptance, echoes and undated fields never advance freshness. Read fallback, including Data Act, cannot confirm or authorize a native command. Preserve last-known evidence, source timestamps and stable registry IDs.

Review exact-head Test and Validate, both supported HA targets, archive/packaging gates, upstream review and live acceptance separately. [Release authority](V3_ARCHITECTURE_CLOSURE.md#release-authority) governs promotion. Issue [#44](https://github.com/npinguin/audi_connect_ha/issues/44) remains the stable gate; [#35](https://github.com/npinguin/audi_connect_ha/issues/35) tracks missing manufacturer identity. The upstream maintainer owns the upstream default and stable release.

The [historical B37–B40 review](https://github.com/npinguin/audi_connect_ha/blob/b245cd62b51b08398166932dcb4f95987b87a4e9/docs/V3_REVIEW.md) remains available at the pinned B40 source. Its historical behavior and field counts are not current B41 instructions. See the feature closure for remaining acceptance.
