# Audi Connect 3.0.0b7 — Declarative Sensor Units & Critical Controls

**Experimental HACS test release — not feature complete.**
This release restores V2-compatible HA sensor metadata through declarative
contracts and adds regressions for the previously working upstream CARIAD
Climate Start/Stop and Wake-up commands.

## Improvements

- V3 sensor units, device classes, state classes, precision and diagnostic
  classification now come from `v3/attribute_contracts.json`, not hardcoded
  branches in the HA entity. It includes 72 historical sensor contracts;
  25 explicitly declare native units and 21 device classes from V2.
- Verified contract examples: state of charge **%**, range **km**, charging
  power **kW**, service time **d**, mileage **km**.
- Source unit transformations belong to API route definitions and use
  Home Assistant's standard unit converters, with a checked destination
  matching the sensor contract. Unknown source-unit conversions are not
  invented.
- Read-only response mapping supports standard RFC 6901 JSON Pointers as
  well as existing dotted V2 paths; `0` and `false` remain valid values.
- Upstream CARIAD regression tests cover:
  - Climate start: `POST /vehicle/v1/vehicles/{VIN}/climatisation/start`
    with **no** JSON body
  - Climate stop: same route family with `/stop`, **no** JSON body
  - Wake-up: `POST /vehicle/v1/vehicles/{VIN}/vehiclewakeuptrigger`
    with an **empty JSON body**
- Keeps the b6 Workbench's three stages, API-family filter, bounded read-only
  auto discovery, per-route redacted result snapshots with timestamps,
  alternate command templates and guarded control tests for Wake-up,
  Climate, Charging, Window Heating and Lock/Unlock.
- `{VIN}` is resolved per selected car; `{SPIN}` is a protected runtime
  placeholder for the approved CARIAD Access Lock/Unlock request body only.

## How to test on an actual Audi

1. Back up HA, install the **3.0.0b7 prerelease** via HACS or the attached
   ZIP, restart HA and keep the same Audi Connect config entry.
2. Choose **V3 — Experimental** and enable the Development Workbench.
3. Inspect Step 1 read-only discovery and its `This vehicle / CARIAD`
   grouping. Check state of charge has **%**, range has **km** and charging
   power has **kW** where those signals were actually discovered.
4. Step 2: choose Remote → Wake or Climate → Start/Stop. Step 3:
   test **one** selected control request while physically present, inspect
   the vehicle, then mark the result Worked/Failed/Uncertain.
5. Check the saved HTTP result, timestamp and redacted response preview.
   A 200/202 is not confirmation of vehicle execution.
6. For Lock/Unlock, verify a valid S-PIN is configured in Audi account
   settings. Never enter or share an S-PIN in the Workbench route template.
7. Verify HA entity IDs and automations, then switch back to V2 — Stable
   in the same entry if a V3 regression affects the installation.

## Known limitations

The upstream command *request shapes* are regression-tested; real-vehicle
success, Audi request-ID polling and readback are still open acceptance gates.
MBB legacy controls, a subset of historical V2 mappings and several HA
platforms remain unimplemented. Two V2 dynamic units are left unresolved
until API response evidence establishes their actual source units.

See **docs/V3_FEATURE_GAPS_3.0.0b7.md** for the prioritized feature gap list.
The release is published only after compilation, all Python/Node tests,
Hassfest, HACS validation and immutable SHA/ZIP/checksum gates pass.
