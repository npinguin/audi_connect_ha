# Audi Connect — Feature Restore Engineering

**Stage:** Read-only discovery only. **Branch:** `feature/restore-audi-data` from fork main `2.5.3b11`.

## Purpose

Restore Audi/CARIAD data that became unavailable after the 2026 Auth0 transition, especially the four existing trip sensors and PHEV fuel/electric consumption. Do not alter stable lock/unlock, flash, climate, charging, entity identifiers or Home Assistant config entries.

## What is already proven versus unknown

- **Proven in code:** Auth0 sessions deliberately disable legacy trip polling: `support_trip_data = not uses_auth0`. Legacy MBB `get_tripdata` cannot be re-enabled merely by flipping this flag.
- **Unverified candidates:** modern `/vehicle/v1/trips/{vin}/...` and `/vehicle/v1/vehicles/{vin}/tripstatistics` endpoints found in independent clients. Their availability, permissions, payloads and units on a particular Audi are unknown.
- **Unverified diagnostics:** `batterySupport`, `tyrePressure` and `vehicleHealthWarnings` selectivestatus jobs. A capability identifier or HTTP 200 does not prove readable vehicle data.
- **Independent channel:** the Audi EU Data Act portal requires separate explicit consent and potentially an independently authenticated session. CARIAD access tokens must not be assumed valid for it.
- **Not in scope yet:** automatic data restoration, new sensors or commands, notifications/push, additional background polling and any conversion to third-party cloud services.

## Feature restore probe — opt-in only

The existing `audiconnect.probe_api_paths` service now accepts **restore: true**.

```yaml
action: audiconnect.probe_api_paths
data:
  device_id: YOUR_HOME_ASSISTANT_AUDI_DEVICE_ID
  restore: true
```

Eight candidate **GET-only** requests, in order:

| Probe | Fixed candidate endpoint |
| --- | --- |
| trip_shortterm | `/vehicle/v1/trips/{vin}/shortterm` |
| trip_longterm | `/vehicle/v1/trips/{vin}/longterm` |
| trip_last | `/vehicle/v1/trips/{vin}/shortterm/last` |
| tripstatistics_shortterm | `/vehicle/v1/vehicles/{vin}/tripstatistics?type=shortTerm` |
| tripstatistics_longterm | `/vehicle/v1/vehicles/{vin}/tripstatistics?type=longTerm` |
| battery_support | `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=batterySupport` |
| tyre_pressure | `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=tyrePressure` |
| vehicle_health_warnings | `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=vehicleHealthWarnings` |

Only a user-triggered service call runs these requests. There are **no** new periodic network calls. The existing device ownership check and 15-minute per-vehicle cooldown apply. `extended` and `restore` are mutually exclusive.

The run requires a known Audi API allowance of **at least 20 remaining calls**, reserves **12 calls**, and stops on 401, 429, 5xx, timeout or transport error. HTTP 403/404 are classified but not mistaken for a lack of vehicle capability. The 8 responses are **discarded**; the next Home Assistant Download Diagnostics export contains only the route label, HTTP status classification, attempt count and timestamp. No raw trip values, precise position, VIN, credentials or response body are persisted.

This is a diagnostic experiment; do **not** interpret a 200 as proof that the returned data is usable for a new sensor.

## Next implementation gates

1. **P0 — trip statistics:** collect safe status results for both endpoint families using a consenting Auth0 tester. Determine which paths actually work before implementing a provider.
2. **P0 — schema and units:** use synthetic test fixtures derived from confirmed *field names and units*, not raw personal driving history. Distinguish last trip, short/long term, and since-refuel statistics; never guess timestamps or units.
3. **P0 — PHEV data:** only after field verification normalize fuel (L/100 km), electric consumption (kWh/100 km), electric distance and recuperation; distinguish absent data from numeric zero.
4. **P1 — diagnostics:** investigate 12V battery, TPMS and warnings only when the Audi API returns a usable vehicle-specific job.
5. **P1 — device identity:** retain current model source/availability semantics; use actual reported metadata rather than inference from a VIN or nickname.
6. **P2 — more controls:** no new charging/climate writes without verified endpoint, permissions, post-action readback and clear experimental gating.
7. **Separate EU Data Act research:** do not add a second authentication system, poll portal files or handle consent automatically in this branch.

Restoring a trip sensor must preserve its existing Home Assistant unique ID and timestamp semantics. Stale values must have explicit freshness, unsupported responses must not permanently disable entities, and 401/403/404/429/5xx must be distinguished. Keep test coverage for the already working Q8 PHEV controls.

## External context and licensing

This engineering plan follows the project-supplied **Audi Connect — API gap analysis beyond Home Assistant**, dated 10 November 2026. Candidate routes came from other projects and do not establish current Audi support:

- https://github.com/TA2k/ioBroker.vw-connect
- https://github.com/tillsteinbach/WeConnect-python
- https://github.com/its-me-prash/vwgroup-connect-ha
- https://github.com/evcc-io/evcc/tree/master/vehicle/vw/eudataact
- https://github.com/audiconnect/audi_connect_ha/issues/907

VW Group Connect is AGPL-3.0 whereas this Audi Connect integration is MIT. **Do not copy AGPL implementation source** into this integration without resolving licensing compatibility. Study endpoint patterns and use independently written code and synthetic tests.

This branch is not an accepted HACS release and must not be merged or submitted upstream as a claim of restored functionality before real API evidence is available.


## 11 November 2026 — upstream review sync and wake / capability roadmap

**Upstream review:** the feature branch now includes the focused regression
corrections from upstream contribution PR #915: identical lock/unlock command
outcome handling, legacy-only remote-engine compatibility fallback and a
fail-closed charge-target update when unknown settings could be overwritten.
The existing selective-status planner already retains previously readable
jobs and is not replaced. This does **not** establish restored Q8 trip schema
or imply that all controls work on every model.

**Q8 climate:** the tested Auth0 Q8 PHEV uses a separate CARIAD climate
ON/OFF command with settings read from the vehicle. The original temperature
control did not work on that vehicle. Preserve the separate modern ON/OFF and
legacy temperature interfaces; do not invent or overwrite target temperatures.

**Vehicle-aware capability vision:** the diagnostics report a coarse vehicle
type, trusted model-family hint and auth generation, without exporting raw
vehicle metadata. These are **research hints only**, never authorization.
Longer-term decisions must combine actual vehicle capabilities, observed
readable jobs, authenticated API generation, and real model-specific outcomes.
A model name is not permission and an incomplete capability list is not proof
that previously functioning sensors must disappear.

**Experimental wake and energy:** the existing Wake Vehicle button remains
opt-in and manual. Per vehicle, in-memory guards restrict requests to one
every **30 minutes**, at most **four attempts per rolling 24 hours**, and
preserve **12 API calls** if Audi reports a remaining quota. Failed requests
count too. These are initial conservative test values, not a measured battery
budget. They reset after HA integration restart. An HTTP acknowledgement
is marked **gateway accepted, physical wake unconfirmed**; the code never
automatically calls another GET or retries the mutation. Diagnostics expose
only timestamp, attempt count, outcome and wait time in an anonymous vehicle
slot, not VIN, battery readings or personal trip data.

**Candidate future trigger design, not yet implemented:** (1) normal passive
cloud refresh, (2) explicit user wake or a verified charging-session/EVSE
transition, (3) check if critical cloud charge/sleep readings are still stale,
(4) one guarded wake after a per-vehicle sleep/energy budget decision,
(5) delayed bounded readback and freshness comparison, and (6) backoff for
429/5xx or inactive parking. Avoid waking merely because a scheduled poll
returned unavailable or the vehicle was parked. Never infer physical wake,
charging resumed, or low battery from one status code.

**Live acceptance needed:** compare normal and post-wake charge/sleep status
at known Q8 sessions, record time to fresh car data and actual 12V/traction
battery impact, and verify budget behavior across restart. Keep generic
model-specific actions and automated wake disabled until evidence warrants
them. This branch remains a draft, distinct from upstream PR #915 and
stable fork main.
