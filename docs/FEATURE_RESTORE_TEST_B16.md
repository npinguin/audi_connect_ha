# Audi Connect 2.5.3b16 — One-click probe actions

**Branch:** `feature/restore-audi-data` (draft PR #15). Test-only HACS beta. Stable fork main stays at `2.5.3b11`; upstream PR #915 is not changed.

## Why the previous screen displayed Unknown error

In Home Assistant Developer Tools → Actions, a blue checkbox **on the left** means **include this optional field**. The toggle **on the right** is the **actual boolean value**. If the user ticks the checkbox next to `restore` but leaves the toggle **off**, the service call contains `restore: false`. When `restore_group: vehicle_health` was selected, the old handler raised `ValueError("Restore group requires restore=true")` and HA displayed `Unknown error`. No health GETs ran.

The earlier form submission without a device selection properly returned the separate `device_id` required validation message. This is not an Audi authentication failure.

## Two new, simple actions

**Vehicle Health (battery, tyres, warnings):**

Developer Tools → Actions → **Probe Audi vehicle health (read-only)**, then choose Audi Q8 and select Perform action.

```yaml
action: audiconnect.probe_vehicle_health
data:
  device_id: YOUR_AUDI_DEVICE_ID
```

**Trip endpoints (read-only availability only):**

```yaml
action: audiconnect.probe_trip_data
data:
  device_id: YOUR_AUDI_DEVICE_ID
```

No `restore`, `extended` or `restore_group` fields are required in these actions. They reuse the exact existing eight-known/core vs three-health/trip probe backend and the same per-vehicle 15-minute cooldown. Each runs at most three explicit CARIAD GETs. When Audi does not report a quota, at most three are allowed. When the quota is known and low, none execute. No scheduled polling or vehicle remote control action is added.

The older advanced `audiconnect.probe_api_paths` is preserved for automations and diagnostics. Invalid combinations and cooldown errors now propagate as readable Home Assistant errors, not unhandled ValueErrors.

## What to send after testing

Download Audi Connect diagnostics. The relevant section is `read_only_api_probes`, containing `mode: "restore"`, `restore_group: "vehicle_health"`, attempt count, status classification per job, and **no** vehicle data or token payload.

If you want to refresh actual trip sensors rather than probe their endpoints, use `audiconnect.refresh_trip_data` separately **after the shared cooldown**. Inspect `trip_restore_attempts` and `trip_read_presence`.

## Install and acceptance

Install 2.5.3b16 HACS prerelease; restart Home Assistant and retain existing config entry. Confirm existing lock/unlock, flash, climate ON/OFF and the established status sensors remain unchanged. Run a dedicated health probe **once**, then immediately download diagnostics. On a subsequent invocation within 15 minutes the backend either reuses matching cached results or reports the cooldown without additional requests.

Static tests are not evidence of live Audi access. HTTP 2xx with a job error or a missing job does not prove 12V/TPMS/warning data is available.
