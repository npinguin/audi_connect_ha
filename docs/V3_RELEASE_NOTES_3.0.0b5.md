# Audi Connect 3.0.0b5 — V3 Capability Discovery Test

**Experimental test release; not feature-complete V2 parity.** Built from the
same integration `audiconnect`. Only one of the V2 and V3 runtimes is active.
V2 remains the default and can be reselected under Options.

## Why test b5

Use real vehicle data to measure V3 coverage against V2, not to assume that
every historical route is valid for each Audi vehicle.

- Global V2 source inventory: 110 raw attribute references, 9 aliases,
  101 distinct read-only attributes, and 22 historical control references.
  An entry in the catalog is **not** a V3 capability verified on a car.
- Separate CARIAD, MBB/legacy and GraphQL family executors, with separated
  credentials, region hosts and read/write policies.
- CARIAD selective-status read-only extraction and shared GET polling with
  per-vehicle route evidence. Only valid discovered fields are eligible for
  entities; no value `unknown` is promoted as a working capability.
- MBB read-only charger/climater response mappings are candidates for
  applicable legacy vehicles; unproven control requests remain blocked.
- Workbench inventory/read-only testing, route selection, evidence, and
  additional candidate paths. Historical references remain separate from
  verified V3 observations. The Climate pilot is retained.
- V2 entity-ID preservation and dynamic read-only sensors/binary sensors are
  implemented for a subset. No other V2 domain is yet claimed complete.
- Location routes are not automatically polled; tests do not send a vehicle
  wake-up or any other control request.

## Test sequence in Home Assistant

1. Keep **V2** selected and record your working entities, states, units, and
   last vehicle capture timestamps. Take a backup before switching.
2. Install the **3.0.0b5 prerelease** through HACS, or extract the attached
   `audi_connect_v3_3.0.0b5.zip` into `config/custom_components/`.
   Restart Home Assistant.
3. Open Audi Connect → **Configure** → select **V3 — Experimental** and enable
   **Development Workbench**; save/reload. Do not create a second config entry.
4. In the Workbench select a vehicle. Review per-capability **Read-only**
   inventory (Known V2 / Not tested / Verified / Stale / Missing mapping).
   Check which API family fits the car before testing a candidate.
5. Test **GET** routes for charging, climate and vehicle status. Verify
   stateOfCharge, chargingState, plugState, freshness/timestamps and which
   response mapping was found. Test optional legacy routes only on an
   applicable legacy-auth car.
6. Activate a successfully tested read-only route, refresh the integration,
   and confirm that its matching HA entity appears and updates without
   duplicated device/entity IDs or excessive requests.
7. Do **not** perform remote-control tests unless present with the vehicle
   and able to confirm the physical result. HTTP 200/202 is not confirmation.
8. If needed, reselect **V2 — Stable** in the same config entry and verify that
   existing entity IDs and automations return.

## Please capture for parity analysis

Report, per vehicle (mask VIN), the API family and model, the number of
read-only fields **verified / stale / mapping missing / not tested**, any
actual V2→V3 missing entity IDs and the affected GET operation.
Do not share tokens, S-PINs, VINs, coordinates or raw private responses.

## Known limitations — do not call this feature-complete

- 101 historical read-only attributes are inventoried, not all proven,
  mapped or supported by the independent V3 runtime.
- Normal runtime polling still prioritizes the Climate/bootstrap discovery
  path plus explicitly selected attributes; all domain-oriented schedules,
  derived entity mappings and platform types are incomplete.
- Legacy authentication and regional endpoints need genuine vehicle tests.
- Charging, lock/unlock, auxiliary heating, timer and other historical
  remote control workflows are **not** fully migrated or physically validated.
- V2 ↔ V3 ↔ V2 rollback on a live HA entity registry, HA restarts and
  vehicle-specific rate limits need end-to-end verification.
- Control experiments remain gated; no automatic POST discovery.
- A 2xx response or old cloud timestamp is not proof of fresh vehicle data.

## Release verification

The release workflow compiles code, runs the complete Python suite and Node
Workbench tests, validates HACS and Hassfest, generates the install ZIP and
publishes the immutable tested SHA plus SHA256 checksum. A failing gate
prevents publication.
