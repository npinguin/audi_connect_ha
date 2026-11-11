# Audi Connect — full V2 → V3 parity matrix

Baseline: V2 from source at `a0f188647e85` (11 Nov 2026); V3 b7 + isolated PR #21 read-only repair.
Decision: **V2 is the acceptance baseline; V3 is not yet compatible. Feature roadmap blocked until parity gate passes.**

## What the labels mean

- `mapped_conditional`: a historical CARIAD response path is declared and a V3 native read-only entity can be created, but this is **not** proof of Q8 runtime parity.
- `candidate_after_manual_proof`: operation and V3 HA control implementation exist but are not activated until per-vehicle validation.
- `partial`: platform/entity exists but does not reproduce V2 behavior.
- `semantic_mismatch`: similar-looking V3 feature is not equivalent to V2 (notably **cloud GET vs vehicle wake POST**).
- `not_migrated`: V2 derived/computed/legacy field without matching V3 mapping.
- `missing`: no V3 HA exposure.
- `v2_experimental=true`: declared in V2 source but not automatically exposed in V2's button setup; do not present it as confirmed working.

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

## Platform completeness

| V2 HA platform | Source inventory / additional dynamic entries | V3 status | Required gate |
|---|---:|---|---|
| `binary_sensor` | 23 | partial: only direct source-mapped attributes; derived V2 doors/windows/lights largely absent | 23 declared binary sensors; platform-specific polarity and security-critical freshness |
| `button` | 9 | partial: 5 gated experimental buttons + separate V3 cloud refresh; V2 flash/engine absent | 9 declared V2 button types; exact controls and requests incl. V2 refresh semantics |
| `climate` | 1 | partial: no target temperature control or restoring V2 last target | same unique ID, target temperature 15–30°C, on/off, status and settings |
| `sensor` | 63 | partial: only historical source-mapped + a few diagnostics; derived composites absent | same unique IDs, 57 declared sensors + 6 supplemental sensors; correct metadata, Recorder and freshness |
| `device_tracker` | 1 | structural V3 entity + bounded parked GET; live unverified | same unique ID; last-parked coordinates with timestamp/privacy and no live-driving claim |
| `lock` | 1 | partial: guarded native lock; not physically verified | same unique ID, S-PIN, request-ID completion, real vehicle readback |
| `number` | 3 | global target native entity added; dynamic profiles and write parity missing | two base SoC sliders + dynamic per-location target slider; bounds 20–100, step 5 |
| `select` | 1 | native preferred charge mode entity added; writing gated/unverified | preferred charge mode select with reported options + safe manual/timer fallback |
| `switch` | 7 | partial: only V3 climate quick switch, six V2 climate settings and preheater absent | 7 V2 switch declarations + climate quick contract |

## V2 control-action and writable-setting parity — all control workstreams

| Priority | Action / setting | V2 entrypoint | V3 b7 gap | V3 acceptance test |
|---|---|---|---|---|
| P0 | Cloud refresh | button.refresh_vehicle_data, service.refresh_cloud_data | V3 cloud GET is not V2 request_current_vehicle_data/wake | GET cloud refresh plus separate POST wake/requestID workflow |
| P0 | Remote vehicle refresh / Wake | button.wake_vehicle_modern, service.refresh_vehicle_data | CARIAD wake candidate, no requestID tracking/wake budget | Explicit wake POST, JSON {}, bounded cooldown, requestID outcome |
| P1 | Flash lights | button.flash_lights | V2 button exists, no V3 operation/native button | Capability honkAndFlash, physical test; never expose horn without explicit scope |
| P0 | Start climatisation (stored) | climate.climatisation, service.start_climate_control | V3 bodyless candidate, no requestID end-to-end | No settings -> bodyless POST, requestID lifecycle and state readback |
| P0 | Climate target temperature/settings start | climate.climatisation, service.start_climate_control | V3 lacks set_temperature and settings/body integration | V2 current temp in climate entity; only explicit setting changes use validated payload |
| P0 | Stop climatisation | climate.climatisation, service.execute_vehicle_action | V3 bodyless candidate, no requestID lifecycle | Keep original ID, readback required |
| P1 | Window heating action on/off | button.start_window_heating_modern/button.stop_window_heating_modern | V3 candidates only, physical Q8 result unverified | Independent button test & status |
| P1 | Window heating settings + at unlock + 4 zones | switch.climatisation_window_heating / climatisation_at_unlock / 4 zone switches | Six V2 persisted-setting switches absent in V3 | GET settings then PUT reviewed body, no blind overwrite |
| P0 | Start/Stop charging | button.start_charging_modern/button.stop_charging_modern, service.execute_vehicle_action | V3 candidates; no requestID result/readback | Separate start/stop, no blind retries, explicit selection |
| P1 | Timed charging | service.execute_vehicle_action(start_timed_charger) | V3 lacks dedicated timed charging command | V2 semantics when supported, no guessed payload |
| P0 | Charge mode manual/timer | select.charge_mode, service.set_charge_mode | V3 select platform missing and PUT adapter absent | PreferredChargeMode, not current chargeMode; preserve mode options |
| P0 | Global charge target | number.target_state_of_charge, service.set_target_soc | V3 number platform missing | 20–100%, step 5; read-modify-write, readback |
| P1 | Current location charge target | number.active_charging_profile_target_soc, service.set_location_charge_target | V3 number platform missing | Resolve current charging profile ID from vehicle, don't guess |
| P1 | Individual profile charge target | number.charge_profile_{profile_id}_target_soc | V3 dynamic number creation missing | Stable unique_id based on immutable profile id; no name-key |
| P1 | Preheater on/off | switch.preheater_active, service.execute_vehicle_action | V3 preheater controls not implemented; legacy MBB POST blocked | Legacy auth, security and status readback |
| P1 | Auxiliary heating with duration | service.start_auxiliary_heating | V3 no native equivalent | Duration 10–60m step10, compatibility and auth checks |
| P0 | Lock/Unlock | lock.lock, service.execute_vehicle_action | S-PIN templating exists; completion unverified | Actual lock state, requestID, S-PIN and no retries |
| P2 | Start/Stop engine | button.start_engine/button.stop_engine, service.start_engine/service.stop_engine | V3 absent; V2 feature gated and model-specific | Never auto-enable on Q8 without OEM capability and risk review |
| P1 | Read-only API probe | service.probe_api_paths | V3 guided read family exists but HA service contract absent | Explicit bounded GET, parity of schema/diagnostics |
| P1 | Local dealer management | service.set_local_dealer, sensor.local_dealer | V3 no service handler or local sensor | Local-only data, no Audi cloud request |

### Service API parity

These are existing V2 Home Assistant service IDs. In b7, V3 used `account=None` and did not register all services; the patch shares account bootstrap and registers the services in both runtimes, but not every V3 service action is implemented. Even when an existing global registration survives another account, its handler expects a V2 account. Restoring only entity controls would therefore still break automations.

| V2 service | Required in V3 |
|---|---|
| `audiconnect.probe_api_paths` | Explicit safe read-only diagnostics |
| `audiconnect.set_local_dealer` | Local-only config, no cloud action |
| `audiconnect.refresh_vehicle_data` | V3-independent implementation with original schema and authorization |
| `audiconnect.execute_vehicle_action` | Preserve action selector, per-vehicle gating and response semantics |
| `audiconnect.start_climate_control` | V3-independent implementation with original schema and authorization |
| `audiconnect.start_auxiliary_heating` | V3-independent implementation with original schema and authorization |
| `audiconnect.set_location_charge_target` | V3-independent implementation with original schema and authorization |
| `audiconnect.set_charge_mode` | V3-independent implementation with original schema and authorization |
| `audiconnect.set_target_soc` | V3-independent implementation with original schema and authorization |
| `audiconnect.start_engine` | V3-independent implementation with original schema and authorization |
| `audiconnect.stop_engine` | V3-independent implementation with original schema and authorization |
| `audiconnect.refresh_cloud_data` | Bounded GET refresh, not vehicle wake |

The `execute_vehicle_action` selector includes **all 11** V2 action names, including `start_timed_charger`, `start_preheater` and `stop_preheater`:

```text
lock, unlock, start_climatisation, stop_climatisation, start_charger, start_timed_charger, stop_charger, start_preheater, stop_preheater, start_window_heating, stop_window_heating
```

**Do not confuse registration with authorization:** a service may be registered globally while a vehicle-dependent mutation must be rejected until that VIN has the OEM capability, required S-PIN/credential and proven command semantics. No automatic POST probing.

### Command execution contract (P0)

For every mutating V2 action: `user action → capability/scope check → exact API family, path and payload → one POST/PUT → requestID (if supplied) → bounded pendingrequests follow-up → vehicle status readback → completed / rejected / unknown`. An HTTP 200/202 is only **accepted**, never physical success. If timed out, do not retry blindly. V2 climate stored start with **no new settings** stays bodyless; wake uses JSON `{}`.

### Legacy/MBB compatibility (P1)

V3's `MBBLegacyExecutor` is GET-only. Restore the V2 legacy per-region home endpoint and applicable climate, charging and preheater action variants separately, with security token/S-PIN authorization. Do not use modern CARIAD routes for legacy vehicles or auto-enable unsupported controls.

## Canonical V2 entity rows (source-derived)

The following rows are exhaustive source declarations, not the number of currently active Q8 entities. V2 has runtime/capability filtering and dynamic charging profiles. The `historical_paths` count describes schema inventory, **not live success**. The 110 historical field references at the end include aliases and duplicated entity keys. There are **109 V2 source entity slots**, plus a separately recorded V3-only climate quick switch.

### sensor

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `last_update_time` | not_migrated | 0 | class=timestamp | P0 |
| `shortterm_current` | not_migrated | 0 | class=timestamp | P2 |
| `shortterm_reset` | not_migrated | 0 | class=timestamp | P2 |
| `longterm_current` | not_migrated | 0 | class=timestamp | P2 |
| `longterm_reset` | not_migrated | 0 | class=timestamp | P2 |
| `model` | not_migrated | 0 | — | P2 |
| `mileage` | mapped_conditional | 1 | unit=km, class=distance, state=total_increasing | P0 |
| `service_adblue_distance` | mapped_conditional | 1 | unit=km, class=distance | P2 |
| `range` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `hybrid_range` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `service_inspection_time` | mapped_conditional | 1 | unit=d | P0 |
| `service_inspection_distance` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `oil_change_time` | mapped_conditional | 1 | unit=d | P0 |
| `oil_change_distance` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `oil_level` | mapped_conditional | 1 | unit=% | P2 |
| `charging_state` | mapped_conditional | 1 | — | P0 |
| `charging_mode` | mapped_conditional | 2 | — | P2 |
| `charging_type` | not_migrated | 0 | — | P2 |
| `energy_flow` | not_migrated | 0 | — | P2 |
| `max_charge_current` | not_migrated | 0 | unit=A, class=current | P2 |
| `charging_current_limit_a` | mapped_conditional | 1 | unit=A, class=current | P2 |
| `charging_current_limit_mode` | mapped_conditional | 1 | — | P2 |
| `charging_plug_auto_unlock` | mapped_conditional | 1 | — | P2 |
| `vehicle_reported_online` | mapped_conditional | 1 | — | P0 |
| `vehicle_reported_active` | mapped_conditional | 1 | — | P2 |
| `primary_engine_type` | not_migrated | 0 | — | P2 |
| `secondary_engine_type` | not_migrated | 0 | — | P2 |
| `primary_engine_range` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `secondary_engine_range` | mapped_conditional | 1 | unit=km, class=distance | P0 |
| `primary_engine_range_percent` | mapped_conditional | 1 | unit=% | P0 |
| `car_type` | mapped_conditional | 1 | — | P2 |
| `secondary_engine_range_percent` | mapped_conditional | 1 | unit=% | P0 |
| `charging_power` | mapped_conditional | 1 | unit=kW, class=power | P0 |
| `actual_charge_rate` | mapped_conditional | 1 | — | P2 |
| `tank_level` | mapped_conditional | 1 | unit=% | P0 |
| `state_of_charge` | mapped_conditional | 1 | unit=%, class=battery | P0 |
| `remaining_charging_time` | mapped_conditional | 1 | — | P0 |
| `charging_complete_time` | not_migrated | 0 | class=timestamp | P2 |
| `target_state_of_charge` | mapped_conditional | 1 | unit=% | P0 |
| `external_power` | mapped_conditional | 1 | — | P2 |
| `plug_led_color` | not_migrated | 0 | — | P2 |
| `doors_trunk_status` | not_migrated | 0 | — | P0 |
| `climatisation_state` | mapped_conditional | 2 | — | P0 |
| `outdoor_temperature` | not_migrated | 0 | unit=°C, class=temperature | P2 |
| `park_time` | not_migrated | 0 | class=timestamp | P2 |
| `position_last_updated` | not_migrated | 0 | class=timestamp | P2 |
| `remaining_climatisation_time` | mapped_conditional | 1 | unit=min | P0 |
| `preheater_duration` | not_migrated | 0 | unit=min | P2 |
| `preheater_remaining` | not_migrated | 0 | unit=min | P2 |
| `active_charging_profile_target_soc` | not_migrated | 0 | unit=%, state=measurement | P2 |
| `active_charging_profile_name` | not_migrated | 0 | — | P2 |
| `active_charging_profile_min_soc` | not_migrated | 0 | unit=% | P2 |
| `preferred_charging_time_start` | not_migrated | 0 | — | P2 |
| `preferred_charging_time_end` | not_migrated | 0 | — | P2 |
| `climatisation_timer_enabled_count` | not_migrated | 0 | — | P2 |
| `next_climatisation_timer_local` | not_migrated | 0 | — | P2 |
| `charging_timer_enabled_count` | not_migrated | 0 | — | P2 |
| `vehicle_data_freshness` | missing | 0 | — | P0 |
| `vehicle_data_age` | partial | 0 | — | P0 |
| `cloud_last_successful_poll` | partial | 0 | — | P0 |
| `local_dealer` | missing | 0 | — | P2 |
| `service_overview` | missing | 0 | — | P2 |
| `api_requests_remaining` | missing | 0 | — | P2 |

### binary_sensor

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `plug_state` | mapped_conditional | 1 | — | P0 |
| `plug_lock_state` | mapped_conditional | 1 | — | P0 |
| `glass_surface_heating` | not_migrated | 0 | — | P2 |
| `sun_roof` | not_migrated | 0 | — | P2 |
| `roof_cover` | not_migrated | 0 | — | P2 |
| `parking_light` | not_migrated | 0 | — | P2 |
| `any_window_open` | not_migrated | 0 | — | P2 |
| `any_door_unlocked` | not_migrated | 0 | — | P2 |
| `any_door_open` | not_migrated | 0 | — | P2 |
| `trunk_unlocked` | not_migrated | 0 | — | P2 |
| `trunk_open` | not_migrated | 0 | — | P2 |
| `hood_open` | not_migrated | 0 | — | P2 |
| `left_front_door_open` | not_migrated | 0 | — | P2 |
| `right_front_door_open` | not_migrated | 0 | — | P2 |
| `left_rear_door_open` | not_migrated | 0 | — | P2 |
| `right_rear_door_open` | not_migrated | 0 | — | P2 |
| `left_front_window_open` | not_migrated | 0 | — | P2 |
| `right_front_window_open` | not_migrated | 0 | — | P2 |
| `left_rear_window_open` | not_migrated | 0 | — | P2 |
| `right_rear_window_open` | not_migrated | 0 | — | P2 |
| `braking_status` | not_migrated | 0 | — | P2 |
| `oil_level_binary` | not_migrated | 0 | — | P2 |
| `is_moving` | not_migrated | 0 | — | P2 |

### button

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `refresh_vehicle_data` | semantic_mismatch | 0 | — | P1 |
| `flash_lights` | missing | 0 | — | P1 |
| `start_charging_modern` | candidate_after_manual_proof (V2 experimental) | 0 | — | P1 |
| `stop_charging_modern` | candidate_after_manual_proof (V2 experimental) | 0 | — | P1 |
| `start_window_heating_modern` | candidate_after_manual_proof (V2 experimental) | 0 | — | P1 |
| `stop_window_heating_modern` | candidate_after_manual_proof (V2 experimental) | 0 | — | P1 |
| `wake_vehicle_modern` | candidate_after_manual_proof (V2 experimental) | 0 | — | P1 |
| `start_engine` | missing | 0 | — | P1 |
| `stop_engine` | missing | 0 | — | P1 |

### switch

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `preheater_active` | missing | 0 | — | P1 |
| `climatisation_window_heating` | missing | 0 | — | P1 |
| `climatisation_at_unlock` | missing | 0 | — | P1 |
| `climatisation_zone_front_left` | missing | 0 | — | P1 |
| `climatisation_zone_front_right` | missing | 0 | — | P1 |
| `climatisation_zone_rear_left` | missing | 0 | — | P1 |
| `climatisation_zone_rear_right` | missing | 0 | — | P1 |


### number

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `target_state_of_charge` | missing (dynamic) | 0 | — | P0 |
| `active_charging_profile_target_soc` | missing (dynamic) | 0 | — | P1 |
| `charge_profile_{profile_id}_target_soc` | missing (dynamic) | 0 | — | P1 |

### select

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `charge_mode` | missing | 0 | — | P1 |

### climate

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `climatisation` | partial | 0 | — | P1 |

### lock

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `lock` | candidate_after_manual_proof | 0 | — | P1 |

### device_tracker

| V2 key / unique ID suffix | V3 static coverage | Historical CARIAD paths | Unit / class contract | Priority |
|---|---|---:|---|---|
| `position` | missing | 0 | — | P2 |

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

## Recorder migration — 13 HA repair warnings

HA displayed 13 *'no longer has a state class'* repairs after V3 activation. The current `attribute_contracts.json` has many `state_class: null` entries; blindly adding `measurement` would corrupt long-term statistics or misrepresent a field. Compare the exact Recorder/entity registry metadata and historical V2 behavior, then explicitly migrate changes with tests. Do not suppress repairs by deleting entities/statistics.

| Repair-affected sensor key | Migration task |
|---|---|
| `sensor.service_inspection_time` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.oil_change_distance` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.primary_engine_range` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.secondary_engine_range` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.tank_level` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.state_of_charge` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.hybrid_range` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.secondary_engine_range_percent` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.service_inspection_distance` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.oil_change_time` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.remaining_climatisation_time` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.primary_engine_range_percent` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |
| `sensor.range` | Compare V2 and V3 device/state classes, units, `state_class`, `unique_id`, restore existing statistics where semantically compatible |

## Shared HA identity and clear device presentation

**Zero user migration** is part of V2 parity: same config entry, VIN device, `unique_id`, `entity_id`, native platform, service identifiers and payload schemas, unit/Recorder metadata, dashboards and automations. Switching via the integration option currently unloads/reloads the config entry; it is not a second login, re-pairing or an instantaneous in-memory switch. Precisely one coordinator performs polling and actions.

The implementation previously disabled 59 registry entries under V3 b7. This patch now restores **only** migration-owned `disabled_by=INTEGRATION` records and never disables historical V2 entries on future V3 loads. Other entities may remain `unavailable` pending V3 data mapping; keeping a registry ID is necessary but **not sufficient** for parity. User-disabled entries are untouched.

V2 upstream platform metadata is immutable. The **V3 declarative metadata** reclassifies 15 vehicle sensor contracts out of Diagnostics, without any V2 sensor or binary sensor code changes. The legacy 11 binary status categories remain unchanged in V2; V3's own binary entities must implement independent metadata and categories. True cloud health (API requests remaining, last poll, freshness, V3 discovery) remains Diagnostic. These changes do not rename or recreate entity IDs and do not invent `state_class`. Existing user-customized categories must be respected by HA.

The target architecture for reusing the **same V2 account/session owner** with an independent selected V2 or V3 engine is defined in [ADR: Shared Account and HA Entity Contract](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md). The shared authentication/session bootstrap is implemented on the patch branch; all-nine-platform and independent V3 control migrations remain open.

## Acceptance gates — release blocked until all hold

1. **Inventory diff**: every V2 entity/service/action has an explicit mapping to the independent V3 runtime, or is explicitly vehicle-unsupported. New V2 source declarations automatically fail an inventory-drift test.
2. **No regression on Q8**: V2's 90 entity registry records remain attached to the same vehicle, no additional integration-disabled historical entities, no duplicate unique IDs, valid last-known telemetry after 1h/4h/24h parking.
3. **Read-only parity**: compare actual values, timestamps, units, polarity, derived fields and unavailable semantics for all Q8 reported capabilities. Mixed CARIAD HTTP 207 and partial cloud failures cannot erase valid values.
4. **Platform parity**: all 9 platforms set up in V3, including number, select, tracker; supplemental freshness, dealer/service, rate-limit and trip-related entities retained according to V2 support.
5. **Control parity**: all V2 HA-native and service actions available for eligible vehicles, with exact historical service IDs and parameters, no test-only workaround needed; physical outcome not inferred from HTTP acceptance.
6. **Safety**: physical commands require per-VIN capability/authorization verification; S-PIN never stored in logs; status readback, request-ID completion, duplicate prevention, bounded wake budget, no blind retries.
7. **Recorder**: review and resolve all 13 warnings by metadata compatibility and proper statistics migration, without inventing state classes.
8. **Legacy + regions**: Auth0/Q8 and legacy MBB paths separately tested; unknown capabilities not labeled permanently unsupported; region allowlists maintained.
9. **Lifecycle**: V2 → V3 → V2 → V3 with no re-pairing, registry deletions, duplicate devices, lost user settings, broken dashboard IDs or automation/service names.
10. **Quality**: pytest, HA test runtime, HACS/hassfest, Workbench, real Q8 acceptance, multi-vehicle comparison, and explicit release-gate signoff.

## Work order / ownership

| Phase | Focus | Stop/Go requirement |
|---|---|---|
| P0-A | Registry 59 disabled vs 0 on V2; complete CARIAD read-only and age behavior (PR #21) | No mass-unavailable regression |
| P0-B | Q8 controls: climate, charging, access, wake, command-ID/pendingrequests | Safe readback on car and no blind retries |
| P0-C | Number/select and service facade without V2 runtime dependency | Existing automations and sliders work |
| P1-A | Derived sensors and 13 Recorder metadata repairs | Values/units/history equivalent to V2 |
| P1-B | Preheater, auxiliary heating, timers/settings, window heating, location profile controls, flash | Eligible vehicle functions and UI available |
| P1-C | MBB/legacy control and read-only parity, GPS/device tracker and dealer metadata | Per-family Q8 + legacy acceptance |
| Gate | Restore all 9 platforms, full diff on Q8 and rollback | Only then resume Media, Trips expansion and roadmap |

Machine-readable baseline: [`docs/V2_V3_PARITY_BASELINE.json`](V2_V3_PARITY_BASELINE.json). It contains all 109 source-defined V2 entity slots, 110 historical field references, V2 service IDs/action choices, V3 catalog operation inventory and current parity classifications. No VIN, token or GPS values are recorded.

