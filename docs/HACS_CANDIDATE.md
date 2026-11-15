# Audi Connect 3.0.0b44 — startup recovery test candidate

Experimental B43 hotfix for local acceptance. V2 remains the default and fallback; V3 is opt-in.

## Fix

- Conflicting observations must not replace previously reviewed mapping evidence with invalid_value.
- Repair the known legacy invalid_value attribute-evidence row on restore, after validating its mapping, source, job and schema. Retain the other reviewed mappings and existing profile, controls, entity IDs and trip history. An affected automatic batch mapping without independent evidence is rediscovered during ordinary polling.
- No new API calls, routes, caches or scheduler. Untrusted mappings are still rejected.

## Acceptance

Back up HA and install this test candidate without deleting the existing integration or device. Restart and confirm startup, preserved discovery and entity history, native status and existing controls. The exact offending row from the reported Q8 has not been inspected. If startup still fails, report the precise exception and sanitized diagnostics; do not reset the profile. B43 physical acceptance remains open.

Source: merged PR #72, b5bfccec85ab58f8b5793187318e94e7b32cb837. Exact-head c57e8aec18d05638d6787968eedd517ae49a5674, Test #2194 and Validate #2195 passed. Packaging validates HA 2026.11.1 and the archive. Stable gate #44 remains open. HACS tag publication requires the existing upstream lag gate; upstream #918 remains on B42 until separately authorized.
