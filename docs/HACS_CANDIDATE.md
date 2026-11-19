# Audi Connect 3.0.0b54 — simpler configuration

Experimental HACS TEST prerelease. V2 remains the default and fallback; V3 is opt-in. This is not a stable release.

## What's changed

- V3 Configure now opens a native Home Assistant menu: General settings, Vehicle setup & discovery, Additional data sources, Service & maintenance, and Advanced & experimental.
- Each settings page saves independently. Ordinary settings no longer mix navigation actions with checkboxes.
- STOP recovery parameters and the reverse geocoding endpoint appear only after explicit enablement. Recovery values use numeric input boxes with the existing limits.
- Existing settings, dealer details, profiles, history, Data Act and physical discovery consent are preserved. V2 retains its existing settings and rollback behavior. Authentication, polling and vehicle command behavior are unchanged.

## Upgrade and test

Back up Home Assistant, update the existing integration and restart. Open Configure and verify navigation, saving and cancellation, disabled features and their retained settings, and V2 rollback on a test installation. No physical command is sent by navigating or saving ordinary settings.

## Known limitations

Live frontend acceptance remains pending. B53 authentication maintenance is included; physical charging STOP reliability and broader live account and vehicle acceptance remain open.
