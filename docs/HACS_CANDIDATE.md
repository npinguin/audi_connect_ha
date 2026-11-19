# Audi Connect 3.0.0b53 — shared authentication maintenance

Experimental HACS TEST prerelease for live acceptance. V2 remains the default and fallback; V3 is opt-in. This is not a stable release.

## What's changed

- V2 and V3 now share one myAudi client identity (5.10.1).
- Market configuration discovery uses the matching app version. A missing version-specific document (HTTP 404/410) permits one fallback to the previously used configuration version; authentication refusals and rate limits are not retried by this mechanism.
- Market migration hints are diagnostic only. Existing authentication provider selection, stored tokens, consent, vehicle identities and history remain unchanged.
- Charging command routes, physical verification, and the default-off STOP recovery policy are unchanged. This release does not claim to solve the Q5 STOP timeout.

## Upgrade and test

Back up Home Assistant and update the existing integration via HACS. Confirm existing sessions continue to work, telemetry refreshes, and token renewal and any required sign-in succeed. If testing remote controls, independently verify the vehicle's physical response. Use a separate test installation or backup for rollback.

## Known limitations

Live account and market compatibility with the new app identity still require validation. Physical charging STOP reliability remains unproven. Share only sanitized diagnostic evidence; do not share credentials, VINs, tokens, raw responses or private locations.
