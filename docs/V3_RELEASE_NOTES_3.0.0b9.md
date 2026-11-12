# Audi Connect 3.0.0b9 — semantic correctness & evidence cockpit

Experimental HACS test only; explicitly authorized by the maintainer. Full CI is required for publication. Not code-complete, not static parity sign-off, not stable.

## Changes
- Oil boolean feeds the existing binary warning sensor; numeric oil percentage is unavailable for a boolean source. Physical warning polarity still needs Q8 confirmation.
- Strict numeric telemetry validation (including percentages and negative remaining-time sentinels), freshness-aware invalidation and no stale overwrite. V3 device classes, units and icons corrected where contracts provide evidence.
- Workbench capability coverage, tested/untested/active/attention/historical operation filters, independent HTTP/schema/binding/physical outcomes, review findings and HA projection counts.
- Bounded redacted GET response field inventory with mapping candidates and quality; no raw sensitive values and no extra Audi requests to build the cockpit. Existing evidence remains readable.
- Existing post-b8 architecture closure and entity rationalization included: separate status/command ownership, persistent guarded command journal, read-only automatic discovery and stable entity identities. V2 runtime fallback remains available.
- Regression tests for semantic values, schema evidence and UI selection. Exact release SHA must pass Python, Node, hassfest and HACS checks.

## Acceptance on the Q8
Back up Home Assistant, select 3.0.0b9 explicitly in HACS and restart. Retain the existing integration entry and choose V3 in options. Verify oil warning state against vehicle, remaining time unknown rather than sentinel, native device classes/units/icons, charging and climate states, cloud vs capture freshness and existing entity history. Inspect Workbench capabilities and API evidence; manually review unmapped ventilation/window heating and other fields. Only deliberately test one physical command when safe; HTTP acceptance alone is insufficient. Export redacted diagnostics after ordinary polling and verify V2 runtime fallback.

No automatic wake, POST/PUT probing or automatic unreviewed feature activation. Model family, partial/absent job observations, dynamic units, physical command results and full V2 parity remain open until evidence supports closure. A backup is required for package downgrade if new local profile fields have been saved; switching runtime to V2 is separate.
