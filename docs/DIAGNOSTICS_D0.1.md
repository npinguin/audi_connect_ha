# Audi Connect D0.1 — privacy-safe diagnostics

**Base:** official `audiconnect/audi_connect_ha` v2.5.2, 2026-11-10.
**Status:** development / not Home Assistant runtime-validated.

This change adds Home Assistant's native **Download diagnostics** to the existing Audi Connect config entry. It makes no additional requests to Audi. No new entity IDs, services, credentials, configuration steps or API action behavior are introduced.

## Included

- Safe allowlisted configuration values: region, API level, scan interval and refresh-after-action.
- Session established (not command authorization); coordinator success/failure type; last poll timestamp and rate limit.
- Anonymized per-vehicle slots with poll capability flags and *presence only* of selected source data keys.
- Entity registry platform totals and disabled totals, without names/IDs.
- Last 40 mutating HTTP responses or GET errors: method, route **category**, status, UTC timestamp, and classified outcome.

No tokens, VIN, email, device/entry IDs, GPS coordinates, URLs, request/response payloads or HTTP headers are exported. Operational timing and counts remain; review diagnostics before sharing.

## How to collect

Settings → Devices & services → Audi Connect → three-dot menu → **Download diagnostics**.

Do not enable `DEBUG_VERBOSE`; existing upstream debugging can log sensitive response details.

## Behavior and limits

- A 200/202 HTTP acknowledgement is **not** proof that the vehicle performed the action.
- Legacy climate/lock actions can still be rejected after Auth0 login; this patch instruments, not repairs, them.
- Some legacy polling capabilities are intentionally disabled under Auth0; diagnostics distinguishes these from missing data.
- Only actual HTTP responses through `AudiAPI.request` appear; network errors before a response and device readback are future D0.2 work.
- Export makes zero remote calls and keeps an in-memory maximum of 40 events; observations reset on integration restart.
- Feature flags describe polling support, not successful actuation.

## Validation

Run targeted tests, then the upstream suite and formatting/lint checks. Test in a non-production Home Assistant instance before merge/release.

## Safe rollout

Do **not** delete the Audi Connect config entry to switch GitHub sources. In Home Assistant 2026.11 Marketplace, **Delete and uninstall** removes the entry and vehicle/entity registrations. Keep the original Marketplace installation until a safe non-destructive source transition is established. Test using an isolated HA instance or a controlled file-only replacement with backups and update management.

**Next:** D0.2 command-lifecycle correlation, then vehicle-specific command fixes.


## D0.2 — explicit read-only API path discovery

Run **Settings → Developer tools → Actions → `audiconnect.probe_api_paths`**
and select exactly one Audi Connect vehicle. The service performs up to **eight
GET requests** to the known CARIAD BFF: capability list, charging status,
charging profiles/timers, climatisation, hybrid auxiliary heating, parked
position and pending requests. It does not enumerate unknown endpoints.

The probe uses the current authenticated session without reauthentication,
and never starts/stops charging, locks doors, changes settings, moves the car
or starts its engine. It is **not** performed during normal polling or
Download diagnostics. Results are held in memory, matched to an anonymized
vehicle slot and embedded in the subsequent standard diagnostics download.

Safeguards:
- one run per vehicle per 15 minutes, reused from cache when repeated
- maximum eight sequential requests; no arbitrary URL or method input
- skip requests if the last known remaining API budget is below 12
- stop after first 401, 429, timeout or general request exception
- no VIN, API URL, headers, token, GPS, response body, trip or account identity
  is ever stored in the probe report
- 200 with a missing/error job does not mean that feature is available
- successful read access **does not prove remote command support**

This is an investigative tool for missing features; avoid unnecessary
repeated scans. Run a manual Audi cloud refresh before the probe only
when needed, not automatically.
