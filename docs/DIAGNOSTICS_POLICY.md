# Audi Connect diagnostics — retained by design, not a second product

**Scope:** fork `main` b11 patch and `feature/restore-audi-data` b12–b16 research.
Home Assistant's native **Download diagnostics** is a permanent support capability.
Do not remove it to clean up probes or engineering leftovers.

## Always available (no extra Audi requests)

- Home Assistant config and entity counts, integration state and Auth0/session presence
- Polling success, last attempt and success time, error **type** only
- API quota information if actually supplied by Audi
- Current vehicle data freshness and *presence*, not actual VIN or values
- Advertised capability inventory with explicit `reported != proven usable` semantics
- Recent API errors and identified remote commands, including the two CARIAD
  wake-up paths (`vehiclewakeup` vs `vehiclewakeuptrigger`)

All values are local snapshots. **Downloading diagnostics must never initiate**
an Audi API request, wake a vehicle, refresh a token, or perform a remote action.

## On-demand troubleshooting (not automatic)

- Existing `probe_api_paths` (Core / Extended) remains supported for scripts.
- Simple `probe_trip_data` and `probe_vehicle_health` actions perform at most
  three, explicit, read-only GET requests. `refresh_trip_data` is a separate,
  explicitly requested trip read, not an always-running probe.
- Probes and trip restore share the existing 15-minute per-vehicle request guard.
- Retain only the latest sanitized report **per vehicle and purpose**, in
  memory. On the feature branch, reports expire after **24 hours** or reset on
  integration restart. Expiry never deletes trip sensor measurements.
- A 2xx response does not prove a working data source. An unrecognized response
  is not converted into a fake sensor value.

## Keep the output lean

- The HTTP event ring retains the **last 20** meaningful observations only.
  Successful token refreshes and unclassified successful internal POST calls
  are noise and should not be exported. Failures remain visible.
- Wake-up requests are reported as **accepted but not vehicle-confirmed**.
  One accepted POST cannot prove the car woke up; compare to normal vehicle
  timestamps separately.
- Failed API requests retain a fixed route category and status, never URL,
  tokens, headers, response body or VIN. The same restriction applies to probe
  output and trip schema fingerprints.
- Avoid duplicate trip keys across generic state-presence vs dedicated trip
  presence diagnostics. Existing diagnostic key names are otherwise kept stable.
- No raw debug payloads, arbitrary response keys, arbitrary exception strings,
  or persistent trip history in the diagnostic export.
- Keep one current engineering handover and test checklist; old release-specific
  testing notes remain accessible through immutable release tags rather than
  accumulating in the active feature branch.

## Regression gate for every patch

1. `pytest` including `test_diagnostic_events.py`,
   `test_diagnostics_snapshot.py`, and (feature branch)
   `test_diagnostic_lifecycle.py` must pass.
2. Home Assistant `hassfest` must pass.
3. Check native diagnostics exports do not trigger Audi traffic, and check
   redaction even when a VIN/token appears in a synthetic input.
4. Verify actual lock/unlock, flash, climate and charging behavior is not
   affected by diagnostic changes.
5. Don't publish a new HACS beta just for log formatting, helper methods or
   expired test documentation. Releases should advance user-visible function.
