# Audi Connect 2.5.3b9 — community test candidate

This is a **pre-release for local Home Assistant / vehicle acceptance**, not an upstream release or a claim of universal vehicle compatibility.

## Included in the current candidate

- Existing integration fixes from the development branch: modern Auth0/CARIAD remote actions, resilience when cloud responses are incomplete, support for additional vehicle status data, capability-aware polling and privacy-conscious diagnostics.
- Existing Home Assistant entity identifiers and services remain the intended compatibility surface. Some vehicle controls are only exposed when supported by vehicle capabilities.
- Additional user-triggered charging, window-heating and wake actions remain **experimental**, opt-in and disabled by default.
- Existing legacy functionality is retained. Legacy means older API paths, **not** necessarily scheduled removal.
- This candidate removes development-specific documentation and installation branding; it does not claim that all upstream parity gaps are closed.

## Important limitations

- Audi APIs, regional authentication, account permissions, and model capability reporting vary.
- An accepted HTTP command does not establish physical vehicle success. Check the vehicle and its later state.
- Partial and rate-limited cloud responses can temporarily make values unavailable.
- Target SOC writes, experimental charging/window-heating/wake actions, and newer optional settings still require vehicle-specific validation.
- A clean install and upgrade regression review must precede upstream submission.

## Local acceptance checklist

1. Back up Home Assistant and the existing Audi Connect integration. **Do not delete the integration's config entry** merely to change HACS sources.
2. Install the `v2.5.3b9` GitHub pre-release from this repository with HACS, once the release workflow has produced the `audiconnect-hacs.zip` asset; restart Home Assistant.
3. Verify existing vehicles, sensors, entity IDs, automations, and services remain present.
4. Verify authentication, token refresh/re-authentication as applicable, and normal polling.
5. Check SOC, charging, range, position, model, availability, and stale-data behavior against myAudi.
6. Safely test climate start/stop, lock/unlock, and flash using the actual vehicle; inspect physical state, not HTTP status alone.
7. Verify extra controls are disabled until explicitly enabled and vehicle capability is confirmed.
8. Record any regression or remaining limitation before an upstream pull request.

## Release validation

The automated GitHub Actions workflow must pass `pytest` and Home Assistant hassfest and publish the HACS ZIP plus checksums. HACS metadata validation is reported separately. Until that workflow succeeds and a real vehicle test is completed, this candidate is **not accepted**.
