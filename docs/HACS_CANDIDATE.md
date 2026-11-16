# Audi Connect 3.0.0b48 — API discovery and status reliability

Experimental HACS test release. V2 remains the default and fallback; V3 is opt-in.

## What's changed

- More precise remote-command feedback: queued, in-progress, not-listed and terminal backend outcomes remain distinct. Later native status is correlated only with the integration's own matching request. Backend acceptance is not physical confirmation.
- Vehicle-specific climate discovery supports selective settings and combinations. Optional settings require independent physical review; a failed optional experiment does not invalidate the separately verified base route.
- Existing electric and combustion range entities use role-aware observations, with original capture times and zero/unknown semantics.
- Parked since retains its existing entity identity. The new Parked in sensor uses local Home Assistant zones only, without external geocoding.
- Additional read-only charging and high-voltage battery technical values and sanitized request diagnostics are available when reported by the vehicle. Automation is an explicit read-only API discovery candidate, not a scheduled request or a new writable profile.
- No extra scheduled Audi requests, automatic command replay, or new credential requirements.

## Upgrade and test

Back up Home Assistant, update the existing integration through HACS and restart. Keep the existing configuration entry, devices and entities. Check retained trip history, entity identities and the freshness of reported values.

Test charging START/STOP against independently measured charging power. Test stored and parameterized climate start, stop, and individual reported settings; confirm actual vehicle behavior. Previously used optional climate settings may require selective Vehicle Setup & Discovery again before they can be controlled. A native setting switch requires both directions to be verified; a base route alone does not prove optional parameters.

## Known limitations

Availability depends on model, market, permissions and vehicle-specific evidence. New readings and controls remain subject to field testing. An accepted request or matching later capture is not proof of physical execution. Data Act delivery may be delayed. No new timer, charging-profile or battery-care write support is claimed.

Report model/year, region, integration and HA versions, expected and actual behavior, relevant timestamps and sanitized Audi Connect diagnostics. Never include credentials, VINs, tokens, private locations or raw responses.
