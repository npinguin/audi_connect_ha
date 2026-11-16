# Audi Connect 3.0.0b47 — control reliability and diagnostics

Experimental HACS test release. V2 remains the default and fallback; V3 is opt-in.

## What's changed

- Consistent, temporary optimistic state for supported remote controls, with a five-minute validity window. Newer valid vehicle observations take precedence. After expiry without newer evidence, the control state is unknown; the last reported observation remains available.
- More reliable recovery after rejected requests, Home Assistant restart and failed optional refreshes. Explicitly supported controls remain usable when their effective state is unknown.
- The existing opt-in refresh-after-action setting can request one eligible vehicle refresh after a known HTTP acceptance when newer native evidence is missing. Existing authorization, cooldown and wake-budget restrictions remain in place.
- Richer sanitized technical diagnostics: actual normalized values, source candidates, capture and receipt times, a bounded charging observation trace and command readback history. No raw responses or private identifiers.
- Existing V2 behavior, entity identities, configuration, trip history and normal polling cadence are preserved.

## Upgrade and test

Back up Home Assistant, update the existing Audi Connect integration through HACS and restart Home Assistant. Keep the existing configuration entry, devices and entities.

Test charging START and STOP independently against actual vehicle behavior and measured charging power. Compare the refresh-after-action option off and on. Test existing climate, access and charging settings, and check the control state after the optimistic validity window and after restart. Do not automatically replay uncertain commands.

## Known limitations

Vehicle coverage depends on model, market and permissions. An accepted request, optimistic state or matching later observation is not proof of physical execution. Data Act readings may be delayed. Charging-mode and SoC discrepancies require vehicle-specific evidence; no new command routes or permissions are inferred.

Report model/year, region, integration and HA versions, expected and actual behavior, relevant timestamps and sanitized Audi Connect diagnostics. Review attachments before sharing; never include credentials, VINs, tokens, private locations or raw responses.
