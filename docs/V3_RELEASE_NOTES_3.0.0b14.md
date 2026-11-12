# Audi Connect 3.0.0b14 — Data Completeness & Runtime Reliability

**Experimental HACS test only.** V2 remains default and fallback. No normal completeness-qualified, stable or upstream release claim. b13 remains immutable.

## Changes since b13

- Retain completed VIN-scoped trip snapshots across context refinement and restarts; missing scopes retry at ordinary poll cadence, without fabricating short-/long-term totals from archive. 
- Recover missing parked position through bounded read-only polling; Flash Lights requires an applicable parking position. No automatic physical commands.
- Optional manufacturer image read is isolated from required inventory; validated Audi HTTPS URL, no credentials or known VIN, existing model entity image. Actual target image remains unvalidated.
- Retry explicitly retryable discovery responses within a maximum of three targeted attempts per job and existing quota reserve. Missing or retryable results do not imply unsupported.
- Preserve per-timer preferred charging windows, numeric connected-service status codes, access request status and climate request group in normalized existing entity attributes. No extra entity IDs or parameter write authority.
- Preserve bounded historical physical review evidence across context changes without restoring authorization; explicit revision only where known.
- Report registry/availability reason, missing trip/parking and stale/invalid capture where evidenced. Unknown causes remain explicitly unresolved.

## b13 Q8 evidence (2026-11-12)

HA 2026.11.1 / b13: 119 registered, 51 available, 41 projected unavailable, 15 registered not offered, 12 disabled. 391 archived trips, zero current trip scopes. 24 trip entities unavailable. Manufacturer model/year and PHEV identity observed. 18/23 jobs assessed, 11 observed; no explicit unsupported jobs. 15 non-truncated job schemas (194 structural fields). Charging capture 458 minutes, most other reported capture ages 5–7 minutes. SOC is separately available; stale charging is not itself proof of a defect. Readiness and chargingProfiles returned HTTP 207 with nested 4112 retry=true. Warning envelope is not proof of healthy state. Command journal and physical review remain independent.

No raw responses, identifiers, credentials, location or private trip records included. b14 results are not yet available. Remaining issues: current trip/parking recovery and restart proof, charging while actually charging, vehicle image, structured values and outstanding schema disposition, health/readiness semantics, coverage and physical tests; multi-model evidence remains incomplete.

## Install / validate

Back up HA. In the existing fork custom repository in HACS, enable beta versions and select 3.0.0b14; restart HA. Keep the same entry, V3 selection if already active. Observe normal polls and next real drive/charge; check restored trips, GPS, model image, timers and service codes, unavailable reasons, quota and freshness. Explicitly test physical commands only when safe; never infer physical success from HTTP. Export sanitized diagnostics after normal polling. Roll back to V2 in integration options if necessary; use a compatible HA backup for package downgrade.

See [machine gate](../governance/V3_COMPLETENESS_GATE.json), [b14 one-time authorization](../governance/B14_EXPERIMENTAL_TEST_RELEASE.json) and [upstream readiness](V3_UPSTREAM_READINESS.md). Exact release SHA must pass all regressions, UI tests, Hassfest, HACS validation and package checksum before publication. Seven ordinary HACS gates remain pending evidence; no upstream gate is overridden.
