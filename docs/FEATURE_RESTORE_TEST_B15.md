# Audi Connect 2.5.3b15 — Q8 modern trip contract verification

**Experimental HACS prerelease only.** Built on b14; no new remote vehicle actions, background trip polling or vendor login mechanisms. Fork `main` stays at b11 and upstream PR #915 remains independent.

## New in b15

- Existing **manual** `audiconnect.refresh_trip_data` action now records a privacy-safe modern CARIAD **schema fingerprint** with every successful response (including responses that cannot be parsed).
- The diagnostic fields are allowlisted fixed names, a response envelope type (`object`, `array`, `other`), `recognized_record` and `timestamp_with_timezone`. It does **not** export trip values, personal IDs, VIN, location, unknown JSON keys, API tokens, or raw payloads.
- A modern unsuffixed `averageFuelConsumption=8.1` remains **8.1 L/100 km**. An ambiguous `81` is **not** converted to 8.1 or displayed as 81. The legacy MBB parser still correctly maps 81 to 8.1 under its original contract.
- Three previously reachable modern routes remain the only manual trip GETs. The same shared 15-minute cooldown and API budget safeguards apply. The existing `shortterm_current`, `longterm_current`, and new `last_trip` entities are populated only on valid, timestamped payloads; `*_reset` values are not inferred.
- All previous b14 trip vs Vehicle Health probe groups remain available.

## Test after installing through HACS and restarting

1. Keep the existing config entry. Confirm manifest version `2.5.3b15`.
2. Leave normal 15-minute vehicle polling alone; verify lock, unlock, flash, and native climate ON/OFF remain available.
3. Run one manual trip read only if the shared cooldown expired:

```yaml
action: audiconnect.refresh_trip_data
data:
  device_id: YOUR_AUDI_DEVICE_ID
```

4. Immediately download Home Assistant Audi Connect diagnostics and examine `trip_restore_attempts`, `trip_read_presence`, `read_only_api_probes` and `rate_limit_remaining_last_observed`.
5. Each successful trip-read entry should now include `schema`, even when the response shape is unknown. Share **only the sanitized diagnostic sections**. Compare any real reported trip attributes to myAudi before using them in automations.
6. If desired, after a fresh 15-minute cooldown, run the Vehicle Health group separately:

```yaml
action: audiconnect.probe_api_paths
data:
  device_id: YOUR_AUDI_DEVICE_ID
  restore: true
  restore_group: vehicle_health
```

## Acceptance limits

A previous probe proved HTTP 2xx on Q8 `shortterm`, `longterm`, and `shortterm/last` routes; it did **not** prove readable trips. A `schema.recognized_record=false` tells us that this current safe parser does not understand the actual response; it is **not** permission to fabricate data or blindly interpret units. A generic HTTP 200 is still not a sensor acceptance test.

The research handover reconciliation, upstream overlap and remaining implementation gates are in `docs/CARIAD_HANDOVER_RECONCILIATION_2026_11_10.md`.
