# Audi Connect 3.0.0b51 — charging STOP recovery

Experimental HACS TEST prerelease for live acceptance. V2 remains the default and fallback; V3 is opt-in. This is not a stable release.

## What's changed

- Optional charging STOP recovery now checks the original and any linked second attempt using the same bounded verification lifecycle. Existing opt-in is retained; configure confirmation timeout, read-only verification interval and window, zero or one additional STOP and final notification.
- Reuse fresh native vehicle captures; otherwise check only the affected vehicle's charging status, not the full account. A cached response cannot authorize a retry. No automatic STOP without an exact terminal timeout, fresh native still-charging evidence, unchanged intent and available quota.
- Diagnostics show recovery outcomes and distinguish observed terminal timeout from generic rejection. Home Assistant can notify even when no retry is sent. No third automatic STOP, replay after restart or additional wake.
- B50 telemetry conflict retention, Data Act portal migration and optional parking address remain included. No changes to V2 defaults or other control eligibility.

## Upgrade and test

Back up Home Assistant, update the existing integration via HACS and restart. Keep existing entries, devices and entities. For V3 STOP testing, enable the optional recovery setting and compare actual charger power and myAudi against the reported outcome. Share sanitized diagnostics and timestamps, including whether a second STOP was sent. Check normal polling, entity history and V2 fallback.

## Known limitations

Physical STOP reliability remains unproven. Audi can return delayed vehicle captures or rejected requests; the integration will not retry without the required evidence. Backend acceptance and matching readback are not proof of physical execution. Vehicle support varies. Do not share credentials, VINs, tokens, raw responses or private locations.
