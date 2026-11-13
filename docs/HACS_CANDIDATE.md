# Audi Connect 3.0.0b33 — experimental runtime cleanup and acceptance

Experimental fork HACS prerelease for live acceptance, not stable and not an upstream release. V2 remains default and fallback; V3 is opt-in and EU Data Act remains disabled by default.

## Changes since B32

- Bound incomplete inventory retries to hourly and remove independent token-renewal trigger. Native status cadence remains unchanged; identity recovery may take longer.
- Consolidate parking observations into the existing writer, retain last-known coordinates and reject invalid/future or older capture times. Movement is not live telemetry without a reliable capture.
- Clarify diagnostics: existing poll attempt count, current-runtime request count, native cloud reachability, latest-per-operation evidence and unknown quota.
- Remove the ignored V2-only startup polling option from V3; retain saved V2 preferences. Complete active V3 options labels and help in EN/NL/DE/FR.
- Bound Data Act reauthentication after a failed resource; successful intermediate or unrelated VIN reads cannot reset the retry guard.
- Consolidated user, engineer and maintainer guidance; no new pollers, entity IDs, native requests or command routes.

Exact PR #45 head passed 1,199 Python and 39 Workbench tests, lint/pre-commit, HACS and hassfest. The candidate workflow separately validates the pinned source on HA 2026.7.0 and 2026.11.1 and verifies the archive checksum. B32 product source is offered in existing upstream PR #918.

## Live acceptance

Back up HA. Install this experimental beta via HACS, keep the existing integration and select V3 if not already enabled. Verify entity IDs, vehicle capture freshness, parking, native polling and quota, restart and V2 rollback. Do not delete the entity registry. For optional Data Act, first ensure an existing authorized portal request works, then enable it in integration options; leave credentials blank only if stored myAudi credentials are available. Verify real delivery, disable and failure isolation. Do not share credentials, VIN, coordinates or raw payloads.

Physical charging start/stop, charge-mode and timer behavior, manufacturer identity, operational mobility cadence, Data Act authorization/delivery and representative vehicle/market acceptance remain open. No automatic vehicle wake or command retries are introduced. No stable release authorization; audit issue #44 remains open.

Source: merged PR #45, e5e826a43e05593fe4519952b467ca27a6499ce8.
