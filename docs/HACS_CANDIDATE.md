# Audi Connect 3.0.0b26 — observation closure beta

Experimental fork prerelease; V2 remains default and fallback. Not a stable upstream release.

- Charging completion time clears when a newer valid zero duration indicates no future estimate. Invalid duration and stale replay remain guarded.
- Native timer projections reuse the typed timer parser; incomplete or truncated timer lists no longer produce a misleading count. Removed timers cannot reappear from an older response.
- Diagnostics distinguish value schemas from error-only and command-request envelopes. Schema capture is not proof of semantic or physical support.
- The HACS release gate validates the fork dev source independently of the upstream review branch. No upstream promotion is required.

Source PR #28 passed Test and Validate (1,121 Python tests). Exact-package CI on both Home Assistant versions is required before publication. No new vehicle API requests, command routes or runtime layers.

Physical Q8 charging and climate verification, vehicle identity, remaining capability/entity reconciliation, representative ICE/PHEV/BEV validation and V2 parity remain open.
