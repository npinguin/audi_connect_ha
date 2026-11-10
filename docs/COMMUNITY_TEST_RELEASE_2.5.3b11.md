# Audi Connect 2.5.3b11 — reliability test candidate

This prerelease builds on **2.5.3b10** and includes the four upstream follow-up reliability fixes from local PR #14. It is a **Home Assistant / HACS vehicle test candidate**, not an official upstream release.

## Changes

- **Command confirmation (#865):** charging and climate actions no longer log *Successfully started* when the gateway accepted a request but the car did not confirm it. Explicit rejections still raise errors; timeout leaves the action *unconfirmed*, not automatically *failed*.
- **Request cancellation (#880):** a cancelled Home Assistant polling task propagates `asyncio.CancelledError` instead of being incorrectly retried as a timeout.
- **Parking-position recovery (#888):** one HTTP 404 no longer permanently disables GPS updates until a restart. Cooldowns are bounded (60 seconds to 1 hour) and retries occur during normal scheduled polls. A valid response resets the cooldown. No extra polling jobs are scheduled.
- **Numeric statistics (#878):** 23 numeric sensor definitions now expose `state_class: measurement`, allowing Home Assistant long-term statistics where the sensor values and units are supported. Mileage stays `total_increasing`.
- Four focused regression test suites added. Automated tests passed on the development branch (484 tests) along with Home Assistant hassfest prior to this version bump.

## Regression checklist

1. Back up Home Assistant and your Audi Connect configuration; **do not delete/recreate the config entry** to update the integration.
2. Install the GitHub prerelease `v2.5.3b11` using HACS when available and restart HA. Confirm the **diagnostics manifest and integration version** both read `2.5.3b11`.
3. Verify the already proven controls still work physically: lock, unlock, flash lights and the **Climatisation ON/OFF** switch.
4. Confirm the two obsolete `Start climate (car settings)` and `Stop climate` button entities are not recreated.
5. Verify that range, SoC, charging power and other numerical measurements are eligible for HA long-term statistics once sufficient statistics have accumulated. Existing history is not backfilled.
6. Monitor charging/climate command logging: an accepted-but-unconfirmed request must not be logged as a physically completed action. Do not issue additional vehicle commands merely to force an unconfirmed result.
7. For parking positions: if Audi temporarily returns 404, position polling should recover on later scheduled updates without an integration reload. Only test this when a natural 404 occurs; do **not** simulate errors against the live vehicle.
8. Check that ordinary telemetry/authentication, other sensors, device/entity IDs and existing automations remain intact.

## Known limitations

- The original Climatisation climate entity and legacy Preheater control did not work on the tested vehicle before this release; they remain present for backwards compatibility.
- Charge mode requests can still be rejected by Audi, even when HTTP transport responds successfully.
- Experimental charging/window heating/manual wake controls remain opt-in and require model-specific validation.
- No restoration of legacy trip data under Auth0 is claimed.
- A successful Audi gateway response does **not** prove the vehicle acted.
- HACS repository metadata validation may warn because Issues are disabled in the fork. This is distinct from the integration pytest and hassfest gates.

## Release gate

GitHub Actions must pass `pytest` and `hassfest`, build the `audiconnect-hacs.zip` asset, publish `v2.5.3b11` as a prerelease and include `SHA256SUMS.txt`. The vehicle regression test remains a separate acceptance step.
