# Audi Connect v2.5.3b6 — Q8 functional gap corrections

## Tested user report (2026-11-10)
Audi Q8 PHEV, Auth0. Owner physically confirmed:
- Working: climate start, climate stop, unlock, flash lights.
- Not working: LOCK (gateway shows HTTP 200, car did not lock).
- Model and Park Time missing in HA; a native GPS tracker already exists.

Keep working actions untouched. This beta does not assert that physical LOCK
is repaired: Audi command-level acceptance alone is insufficient.

## Actual fixes
1. Model: Audi media.longName -> media.shortName -> user nickname (last resort);
   model_source marks whether nickname is merely a display label. Prevent
   device model "Unknown ()" when the model year is unavailable. Retain VIN-based
   device identifier and Model sensor unique ID.
2. Park Time: legacy vehicleParkingClock when available, otherwise the
   parkingposition carCapturedTimestamp already received from Audi.
   The fallback is labeled as a last parked-position capture estimate, **not**
   as verified parking-start or engine-off time. Original Park Time sensor
   unique ID is retained.
3. Native device_tracker Position: keep Home Assistant GPS entity (no duplicate
   "person" or tracker), add last-known parked location provenance, timestamp,
   position age and freshness. No added polling or API calls.
4. Lock: after POST and the pre-existing refresh, only treat LOCK as successful
   when the reported car-wide door lock state says "locked". If unlocked or
   indeterminate, raise an informative HA unconfirmed error, not "success".
   Never automatically retry lock or unlock on another API; 429 was observed.
   This does not itself cause a vehicle that rejected the action to lock.
5. Native diagnostics include model and park timestamp *source classifications*
   only, not the model string, VIN or GPS coordinates.

## Check acceptance in HA
- Update to v2.5.3b6 via existing HACS integration with backup, restart HA.
- Under Audi device, inspect Model sensor: a manufacturer name when available,
  otherwise nickname_fallback in sensor attributes (not an Audi-verified model).
- Park Time should appear if Audi reported a timestamp. Look for attribute
  estimated=true when based on the last parked location observation.
- Use the existing GPS Position device_tracker on an HA map; coordinates may
  remain old while the vehicle is asleep. Never treat it like live phone GPS.
- Physically verify LOCK while beside a parked car, all doors/boot shut, key
  safely outside. If HA says not confirmed, do not repeatedly press it; check
  myAudi command history and car state.
- Verify existing Unlock, Start climate, Stop climate, Flash still operate.
- The release is **not LOCK accepted** until the owner physically verifies it.

## Open upstream/backend issues
See docs/Q8_GAP_AUDIT_2026-11-10.md.
- Audi/CARIAD can accept an access/lock request (HTTP 200) while the real
  vehicle doesn't actuate; no proof yet whether this is an application-level
  rejection, vehicle safety precondition, stale status or account entitlement.
- The last diagnostic log includes HTTP 429 after repeated access actions.
- Trip data still unavailable with Auth0 legacy polling disabled (#907).
- Auxiliary heating not reported, and former preheater returned 502.
- Charging profiles and mode writes remain unverified, despite readable charge data.
- GitHub repository settings Issues/default-branch remain an independent
  HACS-validation task for the repository administrator.
