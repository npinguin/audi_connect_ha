# Audi Connect v2.5.3b12 — isolated Feature Restore probe test

**Scope:** experimental read-only diagnostic probes on the separate `feature/restore-audi-data` branch. This is NOT a claim that missing trip, PHEV, 12V, tyre-pressure or warning sensors have been restored.

## Preconditions

1. Back up your Home Assistant instance and existing integration configuration.
2. Install the `v2.5.3b12` prerelease through HACS once published. Restart Home Assistant. Never delete/recreate the config entry just to update the integration.
3. Verify the integration's diagnostics show version `2.5.3b12`. Your previously working lock, unlock, flash and climate ON/OFF controls must remain.
4. Check your Audi API remaining-call budget. This probe requires a known allowance of at least 20 remaining calls and reserves at least 12. Do not run repeated probes merely to produce a different result.

## Run the restore probe

Home Assistant → Developer Tools → Actions → `audiconnect.probe_api_paths`:

```yaml
action: audiconnect.probe_api_paths
data:
  device_id: YOUR_AUDI_DEVICE_ID
  restore: true
```

Select your actual Audi device in the service UI. Leave `extended` disabled: extended and restore are mutually exclusive. After the action, download Audi Connect diagnostics via Settings → Devices & Services.

Inspect **only** the sanitized `read_only_api_probes` section. It lists fixed probe names, status classifications, request counts and timestamp; no raw API payload, VIN, GPS, personal trip data or tokens are retained by this code.

## Expected probe names

`trip_shortterm`, `trip_longterm`, `trip_last`, `tripstatistics_shortterm`, `tripstatistics_longterm`, `battery_support`, `tyre_pressure`, `vehicle_health_warnings`.

A 200 with nonempty JSON is only evidence that a route was readable, not proof of a valid trip statistic. A 404 is `route_not_found_or_not_provisioned`, not proof the car lacks the capability. A 401, 429, 5xx, timeout or transport error stops remaining probes.

## Required regression

- Normal scheduled polling and the Audi cloud session still work.
- Lock/unlock, flash lights and the stateful Climatisation ON/OFF remain functional.
- The original Preheater and legacy climate entity remain present but are not claimed fixed.
- Charge-mode rejection remains a known limitation.
- Existing sensor and service unique IDs are unchanged.
- No new automatic trips, 12V or TPMS sensors should appear at this stage.

**Gate:** Do not promote or submit restoration to upstream until real vehicle results establish supported endpoint families, response schemas, timestamps and units. Avoid sharing raw diagnostic exports without redaction of unrelated personal details.
