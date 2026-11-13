# Audi Connect 3.0.0b28 — freshness and diagnostics consolidation

Experimental fork prerelease; V2 remains default and fallback. Not a stable upstream release.

- Uniform per-entity capture and cloud-observation metadata across telemetry and relevant state/settings entities, using the existing shared freshness module.
- Vehicle data age identifies the latest valid vehicle capture, its source and observed coverage. The derived summary is excluded from its own inputs.
- Access summaries and diagnostics reuse the same freshness logic; private custom source identifiers are not exported.
- Existing entity IDs and compatibility aliases retained. No extra API calls, sensors, polling timers or runtime modules.
- Product documentation and regression tests updated. PR #31 passed Test and Validate (1,128 Python tests, 5 warnings).

The previous published B27 source is already offered in upstream PR #918. B28 must pass exact-package HACS CI and the upstream lag gate before publication. Upstream review is not automatically changed.

Physical Q8 verification, including the previous overnight zero-age observation, remains open. Vehicle capture freshness is distinct from cloud receipt, command projection and historical trip timestamps.
