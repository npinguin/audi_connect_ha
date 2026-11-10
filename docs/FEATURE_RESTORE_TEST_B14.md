# Audi Connect 2.5.3b14 — Trip Data + Vehicle Health test

This is an isolated **feature-branch HACS prerelease**, not an upstream release. It includes previously proven Audi Connect b11/b13 controls and diagnostics. Main remains b11. No background trips, TPMS, 12V or warnings polling is enabled.

## What's new

### 1. Separate read-only Restore probe groups

Home Assistant → Developer Tools → Actions → **Audi Connect: Probe known read-only Audi API paths**.

**Vehicle Health** — select your Audi device and run:

```yaml
action: audiconnect.probe_api_paths
data:
  device_id: YOUR_AUDI_DEVICE_ID
  restore: true
  restore_group: vehicle_health
```

This makes at most three explicit GETs on the active CARIAD bearer:
- `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=batterySupport`
- `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=tyrePressure`
- `/vehicle/v1/vehicles/{vin}/selectivestatus?jobs=vehicleHealthWarnings`

Download diagnostics and inspect only **`read_only_api_probes`** for route status and job outcome. An HTTP 200 with a missing job is **not** positive evidence of usable values; a 404 is not evidence the vehicle itself has no such capability. No 12V, TPMS or warning sensors are created in this version.

**Trip Data probe** (not the same as reading into HA trip sensors):

```yaml
action: audiconnect.probe_api_paths
data:
  device_id: YOUR_AUDI_DEVICE_ID
  restore: true
  restore_group: trips
```

Tests the three 2xx routes already observed on the Audi Q8: shortterm, longterm and shortterm/last. The two rejected `tripstatistics?type=...` alternatives were removed from routine scans.

### 2. Explicit modern trip reader → existing HA trip entities

After the shared 15-minute cooldown, run:

```yaml
action: audiconnect.refresh_trip_data
data:
  device_id: YOUR_AUDI_DEVICE_ID
```

Reads three allowlisted GET routes with Auth0/CARIAD, then normalizes only timestamps and fields with known semantics and measurement units. The existing `shortterm_current` and `longterm_current` sensor unique IDs are preserved. `Last trip (CARIAD)` is a new timestamp sensor with data attributes. The existing `*_reset` trip sensors remain `unavailable` unless independently proven data exists; no reset data is inferred. Unknown JSON schemas do **not** produce fabricated values.

Download diagnostics and inspect **`trip_restore_attempts`** and **`trip_read_presence`**. The report contains only fixed route labels and status classifications; no raw trip history, VIN, token or GPS is retained by diagnostics.

The previously tested endpoints returned HTTP 2xx, but **their real JSON field names and units on the Q8 have not yet been confirmed**. A read can report `no_supported_timestamp_or_trip_schema` or `no_unambiguous_numeric_trip_fields`. This is expected and safe. It tells us the next mapping investigation without claiming restored data.

## Safety

- Only user-requested GETs; no cloud or vehicle mutation.
- Shared per-vehicle 15-minute cooldown across all probe groups and trip reads. Do not try one group immediately after another. Download diagnostics before the next test because it records the last report.
- With unknown Audi rate-limit budget: maximum three requests per explicit action, and no automatic retry.
- With a known low budget: no requests. Require at least 20 remaining; retain a minimum allowance of 12.
- Stop a probe burst on authentication failure, rate limiting, 5xx and transport errors; stop manual trip reads on 401/403/429/5xx and timeout.
- Normal vehicle status polling, known-good lock/unlock, flash, stateful climate and other charging controls are unchanged.
- Back up Home Assistant; install HACS v2.5.3b14 and restart without deleting/recreating the Audi Connect config entry.

## Recommended test sequence

1. **Vehicle Health probe first**, so 12V / TPMS / warnings get their first real Audi HTTP verdict.
2. Download the diagnostics, and share the sanitized `read_only_api_probes` report.
3. After 15 minutes, run `audiconnect.refresh_trip_data`. Download diagnostics again; share `trip_restore_attempts` and `trip_read_presence`.
4. Check whether trip sensors became available, and verify the values against myAudi before trusting them for reporting or automations.

Do not enable continuous background trip polling until the Q8 schema, freshness and API budget are understood. The two original alternative `tripstatistics` routes that returned 404 are not re-enabled.
