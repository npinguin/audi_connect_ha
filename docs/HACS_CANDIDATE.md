# Audi Connect 3.0.0b29 — live correctness and control UX

Experimental fork prerelease; V2 remains default and fallback. Not a stable upstream release.

- Global freshness excludes structural envelopes and adds partial freshness for mixed-age usable captures; automations comparing the global enum should account for partial.
- Correct invalid window evidence, derived timestamp provenance, empty/request-only schemas, and historical versus live mapping evidence.
- Accepted comfort commands publish immediate effective-state feedback without fabricating telemetry. Lock/unlock remain security-sensitive; native pending state stays visible and a later valid contrary capture closes an accepted attempt as readback_mismatch, without retrying or claiming physical failure.
- Common per-control metadata for native HA controls, with legacy aliases preserved. Profile-specific target command correlation remains unavailable rather than inferred.
- PR #32: 1,138 tests passed, five warnings; lint, Hassfest and HACS validation passed. No new entities, API routes, runtime modules or extra polling.

Source is also offered in upstream PR #918 (manifest 2.5.2). Exact-package HACS gates remain required. Physical Q8 acceptance, long-run lock recovery and other OEM gaps remain open; stable release remains NO GO.
