# ADR — Shared Audi account, switchable V2/V3 runtime and stable HA entities

**Status:** architecture boundaries and all-nine-platform forwarding implemented in draft PR #21; functional V2 parity and Q8 live acceptance remain open.
**Priority:** V2 parity first. Media, new Trips and other roadmap features remain out of scope until validated.

## Objective

One Audi Connect integration installation and config entry. Reuse the existing V2 Audi account, authentication, region, credentials, S-PIN, VIN ownership and Home Assistant device registry. Let the user switch the selected data/command engine between V2 and V3 without reconfiguration or changing entity IDs in dashboards, templates, scripts, automations, Recorder/statistics or RHI Mobility references.

The switch currently triggers a Home Assistant config-entry unload/reload, **not** a zero-downtime hot swap. No new login or pairing should be required and only one active engine may poll/send commands.

## Reality in b7, versus target

| Layer | Existing V3 implementation | Required target |
|---|---|---|
| Config entry | Same V2 entry, options switch | Keep |
| Account | b7 had `AudiRuntimeData(account=None)`; patch now shares the account | Retain one account/session owner |
| Authentication | V3Auth now shares the existing AudiAccount session/service and token lifecycle | Keep bootstrap seam narrow; never invoke V2 business polling |
| Polling | Independent V3 coordinator, separate from V2 | Keep exactly one active coordinator |
| Data model | Independent V3 Vehicle/attribute schema | Keep V3 clean; normalized fields feed the old HA contracts |
| HA service routing | V2-only service registration, handlers resolve V2 `config_vehicles` | One service facade, dispatch to active engine by VIN |
| HA platforms | All nine are forwarded to V3-owned setup; number/select/tracker are structurally added | Complete real read/write parity and vehicle-specific derived entities |
| Registry handling | Legacy V3 migration disabled historical entries (59 in Q8 diagnostic) | Never disable/remove V2 IDs on runtime change; restore recorded disablements |
| HA metadata | 15 car sensors and 11 car binary sensors tagged diagnostic in V2 | Vehicle data in ordinary Sensors/Binary sensors, technical health in Diagnostics |

The shared account must **not** mean V3 secretly calls `AudiAccount.async_refresh_data` or V2 vehicle methods: these start V2 polling and transformations. Reuse login/session/device identity but dispatch data reads/commands to the selected independent runtime.

## Architecture

```text
Audi Connect config entry / account / session / refresh token / region
 ├─ stable HA device (identifier = VIN), stable entity unique IDs
 ├─ stable native HA entity contracts, all nine platforms
 ├─ stable audiconnect.* service IDs and parameters
 ├─ dispatch + command authorization layer
 └─ runtime switch (HA config-entry reload; one active owner)
     ├─ V2: existing coordinator/vehicle model/command adapter
     └─ V3: new coordinator/normalized attrs/declared API executors
```

### Identity contract

- Do not rename `entity_id` or `unique_id`; `{vin_lower}_{platform}_{key}` is canonical, plus existing account-level IDs.
- A V3 entity that represents a historical V2 function MUST reuse the exact V2 unique ID and HA platform; a new V3-specific entity gets a distinct name without hijacking an existing V2 ID.
- No duplicate vehicle devices, no delete/recreate of the config entry or entity registry, no user setting overwrite.
- Missing/old cloud data may make an entity unavailable, but **never** mass-disable registry entries or silently change IDs.
- Respect `RegistryEntryDisabler.USER`. Restore only integration disablements previously recorded by our own V3 visibility migration.
- Capability-disabled commands are safely unavailable or rejected; the user-visible entity identity remains stable.

### Presentation contract

Home Assistant entity category is NOT the data's API capability and NOT `device_class` or `state_class`.

- **Sensors / Binary sensors:** vehicle data (SoC, range, mileage, charging, doors/windows/lights, parking, maintenance, driving, charge profiles/timers).
- **Controls:** climate, charging buttons, numbers, select, lock; preserve device-level native HA UI.
- **Configuration:** vehicle configurable options, e.g. climate zones, at unlock, window heating.
- **Diagnostics:** integration/cloud health only (last poll, cloud quota, API errors, data freshness and age, discovery, retry/quota). Maintenance warnings belong to vehicle state, not cloud diagnostics.
- Source conversion in API definitions; semantic unit/device class/state class/precision in attribute contracts. HA entities only present normalized values.
- Do not fabricate Recorder `state_class` just to silence existing repair warnings. Check statistics against V2 separately.
- Reclassify **V3 only**; V2 keeps historical upstream presentation. Changes to V3 category never modify unique IDs or delete Recorder history.

### Service contract

Register every V2 HA service under the same `audiconnect.*` identifier in either runtime. Resolve the VIN from the HA device registry, check ownership and V3/V2 selection, invoke the **current** runtime adapter. Keep all schemas, aliases and 11 execute_vehicle_action options. A shared account does not authorize a command.

Every physical command: explicit user action → VIN capability and credentials → exact safe API family/payload → requestID pending/finished check → observed vehicle readback. Accepted HTTP != completed physical action. No automatic POST, no blind retries and no S-PIN leakage.

### Implementation stages

1. **Implemented in patch branch:** stop V3 registry auto-disable; restore old integration-disabled registry entries owned by the config entry. Reclassify ordinary vehicle data **only in V3**. Keep V2 source metadata untouched. Add drift and identity tests.
2. **Implemented in patch:** V3 bootstraps the existing `AudiAccount` authentication and token owner without executing the V2 vehicle poll. V3 retains its independent API and data engine.
3. **Partially implemented:** existing `audiconnect.*` names dispatch into `v3/service_commands.py`; known candidate controls use V3Engine. Other actions explicitly fail closed; full functionality is still required.
4. **Partially implemented:** all nine HA domains have independent V3 setup and historical IDs. Number/select have native read surfaces but require verified V3 setting routes; parked tracker has a bounded CARIAD GET and still needs Q8 verification. Dynamic profile numbers and derived V2 sensor parity remain open.
5. **Partially implemented:** bounded CARIAD `pendingrequests` follow-up now distinguishes backend completion from physical readback. Missing: all V2 read-only fields, derived statuses, settings, physical readback, legacy MBB controls and 13 Recorder migrations.
6. **Required accept:** V2→V3→V2→V3 on the Q8, no renames or HA code changes, active polling and service calls work, physical actions validated on authorized vehicle.

The [full parity matrix](V2_V3_PARITY_MATRIX.md) and [JSON baseline](V2_V3_PARITY_BASELINE.json) are the per-feature checklist; this ADR is the architecture/identity/presentation contract. Keep V2 the production fallback until all gates pass.

## Product surface exclusion

Temporary API probe actions belong to engineering validation, not the V3 product. Neither runtime registers the four fork-only probe actions. Normal V3 polling supplies trip entities. The original upstream V2 business implementation stays unchanged. The optional developer Workbench is separate from the public HA action contract.


## Architecture closure and end-user control discovery (target)

The [Architecture Closure](V3_ARCHITECTURE_CLOSURE.md) and [ADR 002](V3_ADR_002_FAST_DISCOVERY.md) preserve this identity contract. Engineering tests remain manual and explicit; normal end-user setup automatically resolves eligible known controls from reviewed catalog evidence and vehicle bindings without actuating the vehicle. A catalog match is not local physical proof. Stable HA IDs, user-disabled entries and V2 rollback remain mandatory; normal commands and Workbench share one persistent lifecycle. The target supersedes per-user mandatory manual activation, not the requirement for physical engineering acceptance.
