# Audi Connect 3.0.0b31 — charging, timer and control-evidence closure

Experimental fork prerelease for real-vehicle validation. V2 remains default and fallback; V3 is opt-in. Not a stable upstream release.

- Verify manual and timer modes individually against the exact built-in operation revision; an empty advertised list is not permission. Native HA select retains only writable options, and exposes the independent reported mode as metadata.
- Distinguish route availability, physical route evidence and temporal dispatch readiness across diagnostics, Workbench and native HA. Discovery candidates do not become normal dispatchable routes without verification.
- Do not invent vehicle time or capture timestamps for climate timer schedules. Distinguish absent, incomplete, zero-enabled and undetermined next single timer evidence.
- Review B30 live diagnostics: access lock/unlock, climate start/stop, wake and flash have stored physical evidence; charging start and window heating start failed physical review. No new polling or API requests.
- PR #34 exact head passed 1,144 Python tests, Workbench tests, lint and Validate. B31 is an experimental candidate for the outstanding physical acceptance, not evidence of completed physical acceptance.

Preceding B30 product source is already offered in upstream PR #918. B31 does not automatically update the upstream review branch. Exact-package HACS checks are mandatory.

Open: Q8 physical mode transitions, charging start/stop and alternative route, climate settings and heating, identity GraphQL partial responses/authorization, timer clock semantics and native entity acceptance. Stable V3 remains NO GO.
