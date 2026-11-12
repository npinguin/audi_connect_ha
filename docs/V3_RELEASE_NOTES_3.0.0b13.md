# Audi Connect 3.0.0b13 — automatic discovery, trip history and telemetry

**Experimental HACS test only.** Explicitly authorized for evidence acquisition on the new candidate. V2 remains default and fallback; no static parity, full completeness, physical acceptance or stable/upstream release is claimed. Existing b12 is immutable.

## Changes since b12

- Automatic user-mode read-only inventory/discovery, including identity retries, all 23 reviewed shared status jobs and applicable standalone modern/legacy trip and parking reads. Explicit unsupported evidence persists per vehicle/context; missing, stale or transient results remain eligible for later polling. No automatic physical actions.
- Separate read assessment, schema capture, canonical attribute normalization and physical control verification indicators. Expanded per-job structural diagnostics with explicit truncation.
- Native charging and window-heating switches when eligible, climate command projection and fresh readback reconciliation. Ten-second ordinary mutation cooldown; accepted wake/refresh does not add a normal mutation cooldown. Unresolved commands and separate experiment guards remain protected.
- Exact-action user-mode consent and physical outcome review; no consent reuse if the candidate route changes.
- Private trip archive with deduplication, persistence and up to 10,000 records per vehicle; up to 50 rows exposed on the history entity, native trip distance/time/speed/fuel/electric metrics and bounded administrative access. OEM lifetime history is not guaranteed.
- Model identity is sourced from manufacturer inventory, independent of nickname and drivetrain. Fuel/electric ranges, SOC, odometer and boolean versus numeric oil level normalization.
- Structured charging profiles, timers, access/lighting, connected services, readiness, warnings/campaigns and battery support; only recognized response values are projected. No inferred 12V voltage or healthy state from an empty warning object.
- Registry compatibility, safe handling of unknown/partial states, preserved user choices and V2 fallback.

## Evidence and limitations

The previous development code passed 943 Python tests, HACS and Hassfest. Exact release SHA must pass full CI, frontend tests, package validation and checksum before publication. The prior b12 Q8 snapshot observed 14/23 jobs; only stored climate start/stop had physical confirmation. These results do not certify b13 or other vehicles.

Eight implementation gates are closed at the recorded regression level. Seven remain implemented pending validation: identity, trip_durable_history, structured_details, health_details, discovery, schema_disposition, upstream_matrix. Live acceptance remains open. See [machine gate](../governance/V3_COMPLETENESS_GATE.json), [one-time authorization](../governance/B13_EXPERIMENTAL_TEST_RELEASE.json), [evidence](V3_COMPLETENESS_TAKEOVER.md) and [upstream checklist](V3_UPSTREAM_READINESS.md). Unknown departure profile schemas, actual OEM history coverage, identity and warning/12V semantics still require live evidence.

## Install and validate

Back up Home Assistant. In the fork custom repository in HACS, explicitly select 3.0.0b13 and restart HA. Keep the existing Audi Connect entry; choose V3 in integration options if not already active. Read-only discovery runs automatically. Test physical actions individually only when safe, using explicit approval and inspection. Confirm model/year, data types, climate/charging status and readback, trip persistence, API quota and discovery coverage. Export fresh sanitized diagnostics after normal polling; verify redaction before sharing. Do not include VIN, credentials, tokens, S-PIN, private trip or location data.

Rollback: select V2 in integration options; package downgrade separately with a compatible backup. Preserve entity registry and automations. No upstream merge or stable promotion is authorized.
