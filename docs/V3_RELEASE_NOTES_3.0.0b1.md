# Audi Connect 3.0.0b1 — V3 Climate experimental prerelease

**Experimental / opt-in. Do not install on a vehicle you cannot safely test.**

- New integration-wide **Runtime generation** option (V2 default; V3 Climate experimental).
- One Audi account, token session, cloud coordinator, refresh interval and existing climate unique ID; no additional background GET.
- Clean V3 climate catalog with auth/context-dependent operation selection, optional status/control, local evidence and anonymized diagnostics.
- For trusted Audi Q8 models using CARIAD, climate ON/OFF uses the previously tested bodyless start / stop paths and vehicle-stored settings. Another Auth0 model does not automatically inherit the Q8 start variant.
- The V3 climate entity does not advertise an unverified target temperature slider. The duplicate CARIAD quick switch is not created in V3 (its registry entry remains for rollback).
- Explicit advanced experimental opt-in when Audi supplied **no** climate capability verdict; explicit negative or impaired remains blocked.
- Existing V2 legacy functions, other domains, settings, scripts and integrations remain physically present during migration.
- A response accepted by the Audi cloud is not physical vehicle confirmation; command routes never auto-retry/fallback.
- V3 runtime evidence remains local and transient. Full self-learning, custom API template editor, community uploads, battery-aware automatic wake and general model support are **not included**.

**Testing:** see [configuration](V3_CONFIGURATION.md), [architecture](V3_ARCHITECTURE.md), and [acceptance matrix](V3_TEST_MATRIX.md).

**Release gate:** package may be published as a GitHub prerelease only after the complete pytest/hassfest/HACS gates pass for the exact SHA. A beta tag does not substitute for live car verification.


**Compatibility baseline:** HACS advertises Home Assistant 2026.7.0+.
The beta documentation and issue tracker point to `npinguin/audi_connect_ha`
rather than upstream, so experimental issue reports stay in the development fork.
The fork's Issues feature must be enabled before HACS validation can pass.


**This is a test prerelease, not an accepted stable vehicle implementation.**
The release can be packaged after CI/HACS technical validation; end-to-end
Q8 climate behavior and in-place migration are beta tests to perform
*after installation*, before any stable promotion.
