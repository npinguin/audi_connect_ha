# Audi Connect 3.0.0b49 — discovery and runtime reliability

Experimental HACS test release. V2 remains the default and fallback; V3 is opt-in.

## What's changed

- Previously unsuccessful reviewed vehicle controls can be tested again without editing their API definitions. Expert discovery allows individual applicable routes to be selected explicitly.
- Manual and Timer charging modes can be tested separately when the vehicle reports charging capability and a native mode but provides an empty options list. Normal controls remain gated by applicable evidence.
- Guided and selective climate discovery use the same vehicle-specific settings; optional settings do not require an unrelated temperature change.
- Charging and climate timer counts follow the selected timer list. Conflicting observations do not appear as a valid current timer count.
- Invalid current climate observations show unknown instead of a historical HVAC state; historical observations and supported control availability are retained separately.
- Explicit read-only rescans can retest previously assessed routes in bounded batches. No additional scheduled Audi requests or new credentials are required.

## Upgrade and test

Back up Home Assistant, update the existing Audi Connect integration through HACS and restart. Retain the existing configuration entry, entities and devices. Check retained trip history and entity identities.

Use Vehicle Setup & Discovery to test one function at a time. Independently verify charging START/STOP against actual charging power, Manual/Timer mode in myAudi or the vehicle, and cabin climate start/stop and selected settings. Confirm physical behavior before accepting discovery results.

## Known limitations

Vehicle support depends on model, market, permissions and vehicle-specific evidence. HTTP acceptance is not physical confirmation. Manufacturer identity can remain unavailable. No new timer, battery-care or charging-profile write support is claimed. Data Act delivery may be delayed.

Report model/year, region, integration and HA versions, expected and actual behavior, relevant timestamps and sanitized diagnostics. Do not share credentials, VINs, tokens, private locations or raw responses.
