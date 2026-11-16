# Audi Connect 3.0.0b50 — charging and parking reliability

Experimental HACS TEST prerelease for live acceptance. V2 remains the default and fallback; V3 is opt-in. This is not a stable release.

## What's changed

- Conflicting native observations retain their conflict boundary across restart. Older or undated data cannot silently replace the conflict; no raw timer or location history is added to the profile store.
- EU Data Act uses the migrated official VW Group portal. Existing native Audi sign-in is unchanged.
- Charging START/STOP reports actual native or clearly marked last-known vehicle state rather than optimistic charging state.
- Optional **Retry failed charging STOP** (off by default): one additional direct CARIAD STOP only after an exact terminal timeout and fresh native evidence that charging continues. No retry on pending or uncertain results, after restart or after a newer explicit action. A failed or unconfirmed second STOP is reported in Home Assistant; no third automatic STOP.
- Optional **Reverse geocoding** (off by default): a separate approximate Parking address sensor, using an authorized HTTPS Nominatim-compatible provider and rounded coordinates. The public OpenStreetMap Nominatim endpoint is not supported. Local Parked in zones and the tracker are unchanged. Home Assistant may record the address in its own history.

## Upgrade and test

Back up Home Assistant, update the existing Audi Connect integration through HACS and restart. Keep the existing config entry, devices and entities. Confirm existing history and identities survive restart, and test V2 fallback if needed.

For V3 physical acceptance, compare START/STOP with actual charging power and myAudi; check terminal request outcomes, the optional bounded retry and its notification. Enable reverse geocoding only with a provider you are authorized to use, then check the separate address, consent withdrawal and unchanged tracker. Reconnect the optional Data Act source if needed and verify delivery independently. No additional periodic Audi polling is introduced.

## Known limitations

Physical effectiveness of STOP recovery, Audi portal recovery and live geocoding/lifecycle acceptance remain unproven. Backend HTTP acceptance is not physical confirmation. Vehicle support varies; manufacturer identity and some fields can be unavailable. No new 12V voltage, timer, battery-care or charging-profile write support is claimed.

Report model/year, region, integration and HA versions, expected and actual behavior, relevant timestamps and sanitized diagnostics. Do not share credentials, VINs, tokens, private locations or raw responses.
