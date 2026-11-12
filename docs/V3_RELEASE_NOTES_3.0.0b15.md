# Audi Connect 3.0.0b15 — Integration Health, Identity & Access

**Experimental HACS test only.** V2 remains default and rollback choice. No normal completeness-qualified, stable or upstream release claim. b14 remains immutable.

## b14 live evidence

HA 2026.11.1 / Q8 Auth0: 119 registered entities, 77 classified projected, 14 projected unavailable/unknown, 16 registered not offered, 12 disabled under the old projection counting rule. All three trip scopes, 391 normalized trips, parking position and five standalone mobility routes recovered. Inventory HTTP 200 returned null manufacturer metadata; image inconclusive. Two job-level HTTP 207 errors (readiness, chargingProfiles, OEM 4112, retry=true); charging capture 515 minutes old. Door/window entities were registered and projected at the diagnostic snapshot; actual values withheld, and later user reported missing information. Access capture was 63 minutes old. No physical control or charging validation claim.

## Changes

- Validated private VIN/region-scoped last-known manufacturer label with source and observation date across restart. Null inventory does not overwrite valid metadata; restored labels cannot authorize remote engine actions. No invented drivetrain or VIN decoding. Existing b14 installs require a successful manufacturer label before the new cache can help.
- Optional manufacturer media recovery: bounded three attempts per runtime at existing inventory checks, respecting quota; no credentials or raw URL in shared diagnostics.
- Three native diagnostic entities per vehicle: Integration status, Last error, Integration problem. Account-level poll/quota information shared, vehicle findings scoped to vehicle. Nested job errors have safe numeric codes, active/recovered state, bounded runtime history. Unknown quota remains unknown. No additional health API calls.
- Two native read-only access summaries: Door status and Window status; component states, door lock states, optional roof components, capture timestamp and freshness, explicit stale/unknown-data state. Existing binary sensors retain freshness guards; no missing/unsupported component becomes closed. No additional access API calls.
- Registry reporting distinguishes HA unknown state from unavailable entity, and an unpressed button from an unavailable control. Control-block explanations reuse the actual resolver where available. Native climate unknown remains unknown, not falsely OFF; no control guard relaxed.
- Persist bounded historical structural field union separately from live session coverage. No raw values or new control authorization; historical union is not current context evidence.
- Tests, ownership and product/matrix alignment. Runtime health and access summaries require target validation. Trip statistics semantics, charging capture while charging, exact command guards and multi-model physical acceptance remain unresolved.

## Install and verify

Back up HA. In the existing fork's HACS custom repository, select 3.0.0b15 prerelease and restart. Keep existing entry and V3 runtime. Check the five new entities and their attributes under the Audi device, observe normal polling, a real drive and charge, and confirm model label recovery across restart after it has been observed. Do not infer current access state from stale information; verify physical commands only explicitly and when safe. Export fresh diagnostics. Roll back to V2 via options if required.

See [machine gate](../governance/V3_COMPLETENESS_GATE.json), [b15 one-time authorization](../governance/B15_EXPERIMENTAL_TEST_RELEASE.json) and [upstream readiness](V3_UPSTREAM_READINESS.md). Full CI, UI checks, Hassfest, HACS and checksum must pass before publishing. Ordinary HACS and upstream gates remain false.
