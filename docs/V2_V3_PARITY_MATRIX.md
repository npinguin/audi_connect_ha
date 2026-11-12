# Audi Connect V2 / V3 parity matrix

**Review:** 87b127c3908f. Original upstream `d12f74c35c1c961f3b040e5cc77acbca2a5cca26`; previous fixbranch `bc1a8a3c73795b6ae54be2b9494b96aae4c630fd`. See [source comparison](V2_V3_SOURCE_COMPARISON.json) and [machine-readable matrix](V2_V3_PARITY_BASELINE.json).

**Decision:** code paths are present for the historical inventory, but code-complete equivalence is not signed off. A HACS test release requires static parity and CI; Q8 and rollback acceptance are stable-release gates, not preconditions for the first test installation.

## Labels

- `mapped_conditional`: an independent V3 path exists; actual source availability and semantics still require verification.
- `candidate_after_manual_proof`: a native control and reviewed route exist; vehicle-specific capability and explicit action consent apply.
- `partial`: known unresolved implementation difference.
- No row has physical Q8 confirmation.

## Current coverage

109 original baseline entity slots across nine platforms, plus the previous fixbranch's `sensor.last_trip`. {"mapped_conditional":84,"partial":3,"candidate_after_manual_proof":22}. All 11 public HA services and 19 control workstreams are inventoried; four engineering probe services deliberately excluded. Nine V2 business files match the pre-repair Git blob hashes exactly. The original upstream comparison is a declaration comparison, not a claim that the fork's V2 equals current upstream byte-for-byte.

## The user's Q8: observed V2 ↔ V3 b7

| Measure | V2 diagnostics | V3 b7 diagnostics |
|---|---|---|
| Registered HA entities | 90 | 90 |
| Disabled by integration/platform | 0 | 59 |
| HA runtime / coordinator | Successful | Successful |
| CARIAD cloud state | Status fields present (29 state keys) | HTTP 207 with 14/23 jobs observed |
| Climate | V2 `climatisationState` key present | `invalid`; V3 climate not readable |
| GPS / parking | V2 `position` key present | No V3 `device_tracker` platform |
| V2 key presence | SoC, charge state, plug, climate, refresh time | V3 does not yet reproduce each value |
| Known Q8 absence | chargingPower; shortterm/longterm current in diagnostic | Do not label these as proven Q8 features |

V2 metadata evidence: downloaded diagnostic `mode: v2`, `disabled_per_platform: {}`. V3 evidence: b7 `mode: v3`, 59 integration-disabled entities, 207 API and invalid climate state. These diagnostics establish the regression, not physical operation of commands.


## Entity-level code paths and remaining gaps

| Entity | Classification | Evidence | Remaining gap |
|---|---|---|---|
| sensor.last_update_time | mapped_conditional | v3/engine.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.shortterm_current | mapped_conditional | v3/trips.py, v3/engine.py, v3/entities.py | MBB current/reset and CARIAD current/last supported; CARIAD reset history not established. |
| sensor.shortterm_reset | mapped_conditional | v3/trips.py, v3/engine.py, v3/entities.py | MBB current/reset and CARIAD current/last supported; CARIAD reset history not established. |
| sensor.longterm_current | mapped_conditional | v3/trips.py, v3/engine.py, v3/entities.py | MBB current/reset and CARIAD current/last supported; CARIAD reset history not established. |
| sensor.longterm_reset | mapped_conditional | v3/trips.py, v3/engine.py, v3/entities.py | MBB current/reset and CARIAD current/last supported; CARIAD reset history not established. |
| sensor.model | mapped_conditional | v3/engine.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.mileage | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.service_adblue_distance | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.range | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.hybrid_range | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.service_inspection_time | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.service_inspection_distance | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.oil_change_time | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.oil_change_distance | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.oil_level | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_state | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_mode | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_type | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.energy_flow | mapped_conditional | v3/legacy_values.py, v3/legacy_read_mappings.py, v3/entities.py | Historical MBB source; modern equivalent not established where the source does not expose it. |
| sensor.max_charge_current | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.charging_current_limit_a | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_current_limit_mode | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_plug_auto_unlock | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.vehicle_reported_online | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.vehicle_reported_active | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.primary_engine_type | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.secondary_engine_type | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.primary_engine_range | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.secondary_engine_range | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.primary_engine_range_percent | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.car_type | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.secondary_engine_range_percent | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_power | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.actual_charge_rate | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.tank_level | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.state_of_charge | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.remaining_charging_time | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.charging_complete_time | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.target_state_of_charge | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.external_power | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.plug_led_color | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.doors_trunk_status | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.climatisation_state | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.outdoor_temperature | mapped_conditional | v3/legacy_values.py, v3/legacy_read_mappings.py, v3/entities.py | Historical MBB source; modern equivalent not established where the source does not expose it. |
| sensor.park_time | mapped_conditional | v3/engine.py, v3/entities.py | Parking endpoint only, quota/registry eligibility; movement is a recent endpoint indication, not live GPS. |
| sensor.position_last_updated | mapped_conditional | v3/engine.py, v3/entities.py | Parking endpoint only, quota/registry eligibility; movement is a recent endpoint indication, not live GPS. |
| sensor.remaining_climatisation_time | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.preheater_duration | partial | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.preheater_remaining | partial | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.active_charging_profile_target_soc | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.active_charging_profile_name | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.active_charging_profile_min_soc | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.preferred_charging_time_start | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.preferred_charging_time_end | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.climatisation_timer_enabled_count | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.next_climatisation_timer_local | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.charging_timer_enabled_count | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| sensor.vehicle_data_freshness | mapped_conditional | v3/entities.py, v3/ha_platforms.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.vehicle_data_age | mapped_conditional | v3/entities.py, v3/ha_platforms.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.cloud_last_successful_poll | mapped_conditional | v3/entities.py, v3/ha_platforms.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.local_dealer | mapped_conditional | v3/entities.py, v3/ha_platforms.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.service_overview | mapped_conditional | v3/entities.py, v3/ha_platforms.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| sensor.api_requests_remaining | partial | v3/entities.py, v3/transport.py | Account-level live quota implemented; V2 restored display after HA restart still needs matching behavior. |
| binary_sensor.plug_state | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| binary_sensor.plug_lock_state | mapped_conditional | v3/historical_catalog.py, v3/attribute_runtime.py, v3/entities.py | Requires applicable Audi response and actual HA state/readback; no live proof. |
| binary_sensor.glass_surface_heating | mapped_conditional | v3/legacy_values.py, v3/legacy_read_mappings.py, v3/entities.py | Historical MBB source; modern equivalent not established where the source does not expose it. |
| binary_sensor.sun_roof | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.roof_cover | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.parking_light | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.any_window_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.any_door_unlocked | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.any_door_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.trunk_unlocked | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.trunk_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.hood_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.left_front_door_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.right_front_door_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.left_rear_door_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.right_rear_door_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.left_front_window_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.right_front_window_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.left_rear_window_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.right_rear_window_open | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.braking_status | mapped_conditional | v3/legacy_values.py, v3/legacy_read_mappings.py, v3/entities.py | Historical MBB source; modern equivalent not established where the source does not expose it. |
| binary_sensor.oil_level_binary | mapped_conditional | v3/derived_values.py, v3/legacy_values.py, v3/entities.py | Source-dependent normalized/derived values; complete component evidence required for negative security states. |
| binary_sensor.is_moving | mapped_conditional | v3/engine.py, v3/entities.py | Parking endpoint only, quota/registry eligibility; movement is a recent endpoint indication, not live GPS. |
| button.refresh_vehicle_data | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.flash_lights | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.start_charging_modern | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.stop_charging_modern | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.start_window_heating_modern | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.stop_window_heating_modern | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.wake_vehicle_modern | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.start_engine | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| button.stop_engine | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.preheater_active | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_window_heating | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_at_unlock | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_zone_front_left | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_zone_front_right | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_zone_rear_left | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| switch.climatisation_zone_rear_right | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| number.target_state_of_charge | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| number.active_charging_profile_target_soc | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| number.charge_profile_{profile_id}_target_soc | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| select.charge_mode | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| climate.climatisation | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| lock.lock | candidate_after_manual_proof | v3/entities.py, v3/ha_platforms.py, v3/engine.py, v3/full_catalog.json | Reviewed route and native entity exist; per-vehicle capability, consent and functional confirmation required. |
| device_tracker.position | mapped_conditional | v3/engine.py, v3/entities.py | Parking endpoint only, quota/registry eligibility; movement is a recent endpoint indication, not live GPS. |
| sensor.last_trip (fixbranch) | mapped_conditional | v3/trips.py, v3/entities.py | CARIAD last-trip response required |

## Control workstreams

| Action | Contract | Implementation and acceptance |
|---|---|---|
| Cloud refresh | button.refresh_vehicle_data, service.refresh_cloud_data | Live functional acceptance pending. Separate native cloud GET and historical remote refresh POST; no conflation. |
| Remote vehicle refresh / Wake | button.wake_vehicle_modern, service.refresh_vehicle_data | Live functional acceptance pending. Reviewed wake and refresh routes, quota/cooldown/request-ID guards. |
| Flash lights | button.flash_lights | Live functional acceptance pending. Native flash button, explicit capability and parked location required. |
| Start climatisation (stored) | climate.climatisation, service.start_climate_control | Live functional acceptance pending. Stored/bodyless CARIAD start plus MBB parameterized start. |
| Climate target temperature/settings start | climate.climatisation, service.start_climate_control | Live functional acceptance pending. 15–30 C setpoint, restore, temperature-bearing start; no start while off. |
| Stop climatisation | climate.climatisation, service.execute_vehicle_action | Live functional acceptance pending. CARIAD and MBB stop; backend confirmation distinct from car state. |
| Window heating action on/off | button.start_window_heating_modern/button.stop_window_heating_modern | Live functional acceptance pending. Explicit window heat start/stop with separate buttons. |
| Window heating settings + at unlock + 4 zones | switch.climatisation_window_heating / climatisation_at_unlock / 4 zone switches | Live functional acceptance pending. Six persisted setting switches and reviewed settings PUT. |
| Start/Stop charging | button.start_charging_modern/button.stop_charging_modern, service.execute_vehicle_action | Live functional acceptance pending. Explicit charging start/stop with bounded request status. |
| Timed charging | service.execute_vehicle_action(start_timed_charger) | Live functional acceptance pending. Timed charging through reviewed execute-action routing; verify actual schedule effect. |
| Charge mode manual/timer | select.charge_mode, service.set_charge_mode | Live functional acceptance pending. Native charge mode select and parameterized PUT. |
| Global charge target | number.target_state_of_charge, service.set_target_soc | Live functional acceptance pending. Native 20–100% number, step 5 and reviewed target PUT. |
| Current location charge target | number.active_charging_profile_target_soc, service.set_location_charge_target | Live functional acceptance pending. Active profile ID resolved from reported profiles. |
| Individual profile charge target | number.charge_profile_{profile_id}_target_soc | Live functional acceptance pending. Per-profile numbers use immutable ID, not profile name. |
| Preheater on/off | switch.preheater_active, service.execute_vehicle_action | Live functional acceptance pending. Preheater switch and CARIAD auxiliary routes; legacy data parsed independently. |
| Auxiliary heating with duration | service.start_auxiliary_heating | Live functional acceptance pending. Explicit duration and S-PIN guarded auxiliary service. |
| Lock/Unlock | lock.lock, service.execute_vehicle_action | Live functional acceptance pending. CARIAD PIN body and MBB challenge-response RLU; bounded completion. |
| Start/Stop engine | button.start_engine/button.stop_engine, service.start_engine/service.stop_engine | Live functional acceptance pending. Capability-restricted engine start/stop; no model-only permission. |
| Local dealer management | service.set_local_dealer, sensor.local_dealer | Live functional acceptance pending. Local dealer and service overview, config-only. |

## Raw historical V2 field-reference inventory

Source: `v3/historical_catalog.py`, 110 source references across 23 selective-status jobs; 53 explicit historical paths; 57 without. These are source paths, not proven V3 mappings.

| Historical ID | Platform/entity | Job | Explicit V2 path |
|---|---|---|---|
| `TOTAL_RANGE` | `sensor.range` | fuelStatus | `fuelStatus.rangeStatus.value.totalRange_km` |
| `TANK_LEVEL_IN_PERCENTAGE` | `sensor.tank_level` | measurements | `measurements.fuelLevelStatus.value.currentFuelLevel_pct` |
| `UTC_TIME_AND_KILOMETER_STATUS` | `sensor.mileage` | measurements | `measurements.odometerStatus.value.odometer` |
| `MAINTENANCE_INTERVAL_TIME_TO_INSPECTION` | `sensor.service_inspection_time` | vehicleHealthInspection | `vehicleHealthInspection.maintenanceStatus.value.inspectionDue_days` |
| `MAINTENANCE_INTERVAL_DISTANCE_TO_INSPECTION` | `sensor.service_inspection_distance` | vehicleHealthInspection | `vehicleHealthInspection.maintenanceStatus.value.inspectionDue_km` |
| `MAINTENANCE_INTERVAL_TIME_TO_OIL_CHANGE` | `sensor.oil_change_time` | vehicleHealthInspection | `vehicleHealthInspection.maintenanceStatus.value.oilServiceDue_days` |
| `MAINTENANCE_INTERVAL_DISTANCE_TO_OIL_CHANGE` | `sensor.oil_change_distance` | vehicleHealthInspection | `vehicleHealthInspection.maintenanceStatus.value.oilServiceDue_km` |
| `OIL_LEVEL_DIPSTICKS_PERCENTAGE` | `sensor.oil_level` | oilLevel | `oilLevel.oilLevelStatus.value.value` |
| `ADBLUE_RANGE` | `sensor.service_adblue_distance` | measurements | `measurements.rangeStatus.value.adBlueRange` |
| `LIGHT_STATUS` | `sensor.vehicle_lights` | vehicleLights | `vehicleLights.lightsStatus.value.lights` |
| `doorLockStatus` | `sensor.door_lock_status` | access | `access.accessStatus.value.doorLockStatus` |
| `carType` | `sensor.car_type` | fuelStatus | `fuelStatus.rangeStatus.value.carType` |
| `engineTypeFirstEngine` | `sensor.engine_type_first_engine` | fuelStatus | `fuelStatus.rangeStatus.value.primaryEngine.type` |
| `primaryEngineRange` | `sensor.primary_engine_range` | fuelStatus | `fuelStatus.rangeStatus.value.primaryEngine.remainingRange_km` |
| `primaryEngineRangePercent` | `sensor.primary_engine_range_percent` | fuelStatus | `fuelStatus.rangeStatus.value.primaryEngine.currentSOC_pct` |
| `engineTypeSecondEngine` | `sensor.engine_type_second_engine` | fuelStatus | `fuelStatus.rangeStatus.value.secondaryEngine.type` |
| `secondaryEngineRange` | `sensor.secondary_engine_range` | fuelStatus | `fuelStatus.rangeStatus.value.secondaryEngine.remainingRange_km` |
| `secondaryEngineRangePercent` | `sensor.secondary_engine_range_percent` | fuelStatus | `fuelStatus.rangeStatus.value.secondaryEngine.currentSOC_pct` |
| `hybridRange` | `sensor.hybrid_range` | fuelStatus | `fuelStatus.rangeStatus.value.totalRange_km` |
| `stateOfCharge` | `sensor.state_of_charge` | charging | `charging.batteryStatus.value.currentSOC_pct` |
| `chargingState` | `sensor.charging_state` | charging | `charging.chargingStatus.value.chargingState` |
| `chargeMode` | `sensor.charging_mode` | charging | `charging.chargingStatus.value.chargeMode` |
| `chargingPower` | `sensor.charging_power` | charging | `charging.chargingStatus.value.chargePower_kW` |
| `actualChargeRate` | `sensor.actual_charge_rate` | charging | `charging.chargingStatus.value.chargeRate_kmph` |
| `chargeType` | `sensor.charge_type` | charging | `charging.chargingStatus.value.chargeType` |
| `targetstateOfCharge` | `sensor.target_state_of_charge` | charging | `charging.chargingSettings.value.targetSOC_pct` |
| `plugState` | `binary_sensor.plug_state` | charging | `charging.plugStatus.value.plugConnectionState` |
| `remainingChargingTime` | `sensor.remaining_charging_time` | charging | `charging.chargingStatus.value.remainingChargingTimeToComplete_min` |
| `plugLockState` | `binary_sensor.plug_lock_state` | charging | `charging.plugStatus.value.plugLockState` |
| `externalPower` | `sensor.external_power` | charging | `charging.plugStatus.value.externalPower` |
| `plugledColor` | `sensor.plugled_color` | charging | `charging.plugStatus.value.ledColor` |
| `climatisationState` | `sensor.climatisation_state` | climatisation | `climatisation.auxiliaryHeatingStatus.value.climatisationState`; `climatisation.climatisationStatus.value.climatisationState` |
| `remainingClimatisationTime` | `sensor.remaining_climatisation_time` | climatisation | `climatisation.climatisationStatus.value.remainingClimatisationTime_min` |
| `preferredChargeMode` | `sensor.charging_mode` | charging | `charging.chargeMode.value.preferredChargeMode` |
| `availableChargeModes` | `diagnostic_only.charging_mode` | charging | `charging.chargeMode.value.availableChargeModes` |
| `climatisationTargetTemperatureC` | `sensor.climatisation_target_temperature_c` | climatisation | `climatisation.climatisationSettings.value.targetTemperature_C` |
| `climatisationTargetTemperatureF` | `sensor.climatisation_target_temperature_f` | climatisation | `climatisation.climatisationSettings.value.targetTemperature_F` |
| `climatisationWindowHeatingEnabled` | `sensor.climatisation_window_heating_enabled` | climatisation | `climatisation.climatisationSettings.value.windowHeatingEnabled` |
| `climatisationAtUnlock` | `sensor.climatisation_at_unlock` | climatisation | `climatisation.climatisationSettings.value.climatizationAtUnlock` |
| `climatisationWithoutExternalPower` | `sensor.climatisation_without_external_power` | climatisation | `climatisation.climatisationSettings.value.climatisationWithoutExternalPower` |
| `climatisationZoneFrontLeft` | `sensor.climatisation_zone_front_left` | climatisation | `climatisation.climatisationSettings.value.zoneFrontLeftEnabled` |
| `climatisationZoneFrontRight` | `sensor.climatisation_zone_front_right` | climatisation | `climatisation.climatisationSettings.value.zoneFrontRightEnabled` |
| `climatisationZoneRearLeft` | `sensor.climatisation_zone_rear_left` | climatisation | `climatisation.climatisationSettings.value.zoneRearLeftEnabled` |
| `climatisationZoneRearRight` | `sensor.climatisation_zone_rear_right` | climatisation | `climatisation.climatisationSettings.value.zoneRearRightEnabled` |
| `chargingCurrentLimitA` | `sensor.charging_current_limit_a` | charging | `charging.chargingSettings.value.maxChargeCurrentAC_A` |
| `chargingCurrentLimitMode` | `sensor.charging_current_limit_mode` | charging | `charging.chargingSettings.value.maxChargeCurrentAC` |
| `chargingPlugAutoUnlock` | `sensor.charging_plug_auto_unlock` | charging | `charging.chargingSettings.value.autoUnlockPlugWhenChargedAC` |
| `vehicleReportedOnline` | `sensor.vehicle_reported_online` | readiness | `readiness.readinessStatus.value.connectionState.isOnline` |
| `vehicleReportedActive` | `sensor.vehicle_reported_active` | readiness | `readiness.readinessStatus.value.connectionState.isActive` |
| `chargingProfiles` | `diagnostic_only.charging_profiles` | chargingProfiles | `chargingProfiles.chargingProfilesStatus.value.profiles` |
| `chargingTimers` | `diagnostic_only.charging_timers` | chargingTimers | `chargingTimers.chargingTimersStatus.value.timers` |
| `climatisationTimers` | `diagnostic_only.climatisation_timers` | climatisationTimers | `climatisationTimers.climatisationTimersStatus.value.timers` |
| `userCapabilities` | `diagnostic_only.user_capabilities` | userCapabilities | `userCapabilities.capabilitiesStatus.value` |
| `last_update_time` | `sensor.last_update_time` | — | — (derived/unmapped) |
| `shortterm_current` | `sensor.shortterm_current` | — | — (derived/unmapped) |
| `shortterm_reset` | `sensor.shortterm_reset` | — | — (derived/unmapped) |
| `longterm_current` | `sensor.longterm_current` | — | — (derived/unmapped) |
| `longterm_reset` | `sensor.longterm_reset` | — | — (derived/unmapped) |
| `model` | `sensor.model` | — | — (derived/unmapped) |
| `mileage` | `sensor.mileage` | — | — (derived/unmapped) |
| `service_adblue_distance` | `sensor.service_adblue_distance` | — | — (derived/unmapped) |
| `range` | `sensor.range` | — | — (derived/unmapped) |
| `service_inspection_time` | `sensor.service_inspection_time` | — | — (derived/unmapped) |
| `service_inspection_distance` | `sensor.service_inspection_distance` | — | — (derived/unmapped) |
| `oil_change_time` | `sensor.oil_change_time` | — | — (derived/unmapped) |
| `oil_change_distance` | `sensor.oil_change_distance` | — | — (derived/unmapped) |
| `oil_level` | `sensor.oil_level` | — | — (derived/unmapped) |
| `charging_type` | `sensor.charging_type` | — | — (derived/unmapped) |
| `energy_flow` | `sensor.energy_flow` | — | — (derived/unmapped) |
| `max_charge_current` | `sensor.max_charge_current` | — | — (derived/unmapped) |
| `primary_engine_type` | `sensor.primary_engine_type` | — | — (derived/unmapped) |
| `secondary_engine_type` | `sensor.secondary_engine_type` | — | — (derived/unmapped) |
| `tank_level` | `sensor.tank_level` | — | — (derived/unmapped) |
| `charging_complete_time` | `sensor.charging_complete_time` | — | — (derived/unmapped) |
| `plug_led_color` | `sensor.plug_led_color` | — | — (derived/unmapped) |
| `doors_trunk_status` | `sensor.doors_trunk_status` | — | — (derived/unmapped) |
| `outdoor_temperature` | `sensor.outdoor_temperature` | — | — (derived/unmapped) |
| `park_time` | `sensor.park_time` | — | — (derived/unmapped) |
| `position_last_updated` | `sensor.position_last_updated` | — | — (derived/unmapped) |
| `preheater_duration` | `sensor.preheater_duration` | — | — (derived/unmapped) |
| `preheater_remaining` | `sensor.preheater_remaining` | — | — (derived/unmapped) |
| `active_charging_profile_target_soc` | `sensor.active_charging_profile_target_soc` | — | — (derived/unmapped) |
| `active_charging_profile_name` | `sensor.active_charging_profile_name` | — | — (derived/unmapped) |
| `active_charging_profile_min_soc` | `sensor.active_charging_profile_min_soc` | — | — (derived/unmapped) |
| `preferred_charging_time_start` | `sensor.preferred_charging_time_start` | — | — (derived/unmapped) |
| `preferred_charging_time_end` | `sensor.preferred_charging_time_end` | — | — (derived/unmapped) |
| `climatisation_timer_enabled_count` | `sensor.climatisation_timer_enabled_count` | — | — (derived/unmapped) |
| `next_climatisation_timer_local` | `sensor.next_climatisation_timer_local` | — | — (derived/unmapped) |
| `charging_timer_enabled_count` | `sensor.charging_timer_enabled_count` | — | — (derived/unmapped) |
| `glass_surface_heating` | `binary_sensor.glass_surface_heating` | — | — (derived/unmapped) |
| `sun_roof` | `binary_sensor.sun_roof` | — | — (derived/unmapped) |
| `roof_cover` | `binary_sensor.roof_cover` | — | — (derived/unmapped) |
| `parking_light` | `binary_sensor.parking_light` | — | — (derived/unmapped) |
| `any_window_open` | `binary_sensor.any_window_open` | — | — (derived/unmapped) |
| `any_door_open` | `binary_sensor.any_door_open` | — | — (derived/unmapped) |
| `trunk_unlocked` | `binary_sensor.trunk_unlocked` | — | — (derived/unmapped) |
| `trunk_open` | `binary_sensor.trunk_open` | — | — (derived/unmapped) |
| `hood_open` | `binary_sensor.hood_open` | — | — (derived/unmapped) |
| `left_front_door_open` | `binary_sensor.left_front_door_open` | — | — (derived/unmapped) |
| `right_front_door_open` | `binary_sensor.right_front_door_open` | — | — (derived/unmapped) |
| `left_rear_door_open` | `binary_sensor.left_rear_door_open` | — | — (derived/unmapped) |
| `right_rear_door_open` | `binary_sensor.right_rear_door_open` | — | — (derived/unmapped) |
| `left_front_window_open` | `binary_sensor.left_front_window_open` | — | — (derived/unmapped) |
| `right_front_window_open` | `binary_sensor.right_front_window_open` | — | — (derived/unmapped) |
| `left_rear_window_open` | `binary_sensor.left_rear_window_open` | — | — (derived/unmapped) |
| `right_rear_window_open` | `binary_sensor.right_rear_window_open` | — | — (derived/unmapped) |
| `braking_status` | `binary_sensor.braking_status` | — | — (derived/unmapped) |
| `oil_level_binary` | `binary_sensor.oil_level_binary` | — | — (derived/unmapped) |
| `is_moving` | `binary_sensor.is_moving` | — | — (derived/unmapped) |
| `any_door_unlocked` | `binary_sensor.any_door_unlocked` | — | — (derived/unmapped) |


## Release gate

- Static source inventory and independent code paths: updated; no physical acceptance implied.
- Open implementation/verification: quota restore display on HA restart; exact legacy timer payload semantics; CARIAD reset-history availability; HA integration behavior and per-vehicle entity availability. No guessed fields or fallback to V2.
- Recorder: all thirteen reported state classes restored; actual migration to be checked in HA.
- Test release remains blocked until code-complete static parity and CI. Physical Q8 and V2→V3→V2 registry rollback are subsequent stable-release acceptance gates.
