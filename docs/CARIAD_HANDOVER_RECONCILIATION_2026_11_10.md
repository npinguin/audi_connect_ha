# Audi Connect — research reconciliation and next pilot gate

**Research base:** engineer handover supplied 10 November 2026, initially referring to upstream Audi Connect v2.5.2.
**Audited implementation:** npinguin/audi_connect_ha feature/restore-audi-data, b14 base. The upstream PR and experimental feature branch are separate lines of work.

## A — Upstream overlap (do not duplicate)

[Upstream PR #915](https://github.com/audiconnect/audi_connect_ha/pull/915) is **our own** `npinguin` contribution, open on 10 November 2026. It covers tested Q8 remote lock/unlock, flash, modern climate commands, cloud outage handling, safe diagnostics, entity IDs and related reliability fixes. It is **not** independent work to cherry-pick, and must not be merged into fork main merely because the feature branch grows.

[Issue #914](https://github.com/audiconnect/audi_connect_ha/issues/914) confirms that a legacy A3 e-tron using an Auth0 session can run climate through a CARIAD BFF command. Model-specific scope matters; b11-b14 tested on one Q8 and does not establish universal physical actuation.

No upstream review comments were present when checked. Do not submit unverified trip recovery as a follow-up claim.

## B — CARIAD trip route evidence

A user-requested read-only **b13** probe, 10 November 2026:
- `GET /vehicle/v1/trips/{vin}/shortterm`: HTTP 2xx, nonempty JSON
- `GET /vehicle/v1/trips/{vin}/longterm`: HTTP 2xx, nonempty JSON
- `GET /vehicle/v1/trips/{vin}/shortterm/last`: HTTP 2xx, nonempty JSON
- Two alternative `/vehicle/v1/vehicles/{vin}/tripstatistics?type=...` routes: HTTP 404

This proves **reachability and a nonempty response only** for the Q8, not that the content follows the VW Transporter schema or contains usable trip readings. The b14 feature branch excludes the two 404 alternatives from routine scans.

The VW Transporter example from [issue #1060](https://github.com/robinostlund/homeassistant-volkswagencarnet/issues/1060) is useful synthetic schema evidence, not proof of an identical Q8 contract:
`data.tripEndTimestamp`, `mileage_km`, `startMileage_km`, `overallMileage_km`, `averageSpeed_kmph`, `travelTime`, `averageFuelConsumption`.

**Next live pilot:** use the user-triggered `audiconnect.refresh_trip_data` service once. Download diagnostics immediately afterwards; `trip_restore_attempts.results[].schema` now includes only known field names, an envelope type, and a timestamp-validity flag. No raw payload, VIN, GPS, trip ID, trip counts, arbitrary keys or values.

## C — Normalization and Home Assistant contracts

- The legacy `TripDataResponse` and old MBB endpoint remain unchanged. Legacy consumption is reported as tenths and requires division by ten.
- Modern Auth0 CARIAD uses a separate `trip_restore.py` normalizer. The supported modern fuel field `averageFuelConsumption=8.1` maps to **8.1**, never 0.81. An ambiguous unsuffixed 81 is not published as 81 or guessed as 8.1.
- Field names that explicitly contain units (e.g. `averageSpeed_kmph`, `averageElectricEngineConsumption_kWh_per_100km`) map only with those units. Missing measurements become `None`, never zero.
- Only timezone-aware and syntactically correct timestamps become HA timestamp sensors. Old trip readings are not overwritten by older results.
- Existing `shortterm_current` and `longterm_current` unique IDs are preserved. A new `last_trip` timestamp entity is created. The two **User Reset** entities retain existing IDs but remain unavailable until a real reset/aggregate contract is proven. Do not manufacture reset values from last-trip records.
- Trip reads are explicit, at most three GETs per invocation, guarded by a 15-minute shared cooldown and API quota awareness. No new background requests or control actions.

## V3 research and PR #915 follow-up (11 November 2026)

The engineering-review V3 summary adds sources that are **not** verified
Q8 API data contracts. The user supplied a research summary, not the complete
606-line file; this document tracks only the claims substantiated below.

### Verified regression and implementation

A code-level regression in the base `capability_jobs.py` planner matched
capability IDs to selected jobs only by literal names. The reported
`oilLevelStatus` can provide the `oilLevel` job, so the second poll could
silently omit usable oil data. In addition, a reduced job list or incomplete
non-error response could replace the entire cached field dictionary.

- Targeted review: [fork draft PR #17](https://github.com/npinguin/audi_connect_ha/pull/17),
  branched from our upstream PR #915, **not merged into #915**.
- Explicit one-way `oilLevelStatus -> oilLevel` alias; no unsupported
  assumptions that `tripStatistics` is a selectivestatus job or that
  `parkingPosition` is anything other than its separate resource.
- Keep previously validated jobs only if a known, fixed GET job actually
  returned nonempty and non-error data. Ignore unsupported arbitrary job
  identifiers, empty objects and error-only responses.
- Keep cached fields/states when the job selection or returned data is
  incomplete. A 200/207 success is **not** necessarily a complete measurement
  snapshot; nested per-job errors must be evaluated separately.
- AudiAPI already accepts HTTP 207 JSON. No duplicate transport handling, no
  extra API requests, no modified remote actions.
- Regression tests cover matching, failing and partly successful jobs,
  data-preservation on partial reports, and zero accidental extra polls.

### Third-party comparisons: requirements only

- [Homey myAudi 1.1.1](https://homey.app/en-tz/app/com.audi.etron/myAudi/):
  dashboard warning lights + per-new-light triggers, charging plug locked
  status, auxiliary heating status, inspection due and independent S-PIN
  validation without re-login. This is **not proof** of Q8 API access. Prioritize
  status readback and supported units before adding HA entities or automations.
- [Symcon A3 8Y PHEV client](https://community.symcon.de/t/myaudi-klasse-fuer-fahrzeugdaten/134904?page=2):
  restored login and general vehicle reads after June 2026 changes, separate
  routes for digital trip history. Park time inferred from trip end is an
  **estimate** only and must never replace a genuine vehicle parking clock.
- Historical openHAB ConnectedCar Java and mixed 207 responses are schema
  research, not current Auth0 implementation or authorization evidence.
  This branch **does not** copy legacy Java sources or incompatible license
  code into the Audi integration.

### Next gates

1. Resolve PR #17 review and merge into upstream-contribution PR #915 only
   after engineering acceptance; protect the same job planning in the fork.
2. Test live sequential Q8 polls to demonstrate oil-level retention and safe
   freshness under incomplete jobs; unit tests alone do not prove car behavior.
3. Implement warning-light triggers, plug lock, auxiliary heater and S-PIN
   verification **only** after readback schema and authorization are confirmed.
4. Continue the already-planned explicit trip refresh and Q8 normalization.
5. Keep native, redacted diagnostics and bounded probe history; no new probes
   simply to duplicate the other integrations' feature lists.

## Additional backlog

1. **P0:** verify actual Q8 schema and unit provenance with `trip_restore_attempts` and existing HA sensor states; protect unit metadata and timestamps.
2. **P0:** map 2 reset sensors only if the returned schema identifies a true user-reset interval; never claim four restored when only two have data.
3. **P1:** extend verified PHEV metrics only with explicit units and observable presence (electric distance, electric consumption, recuperation, fuel consumption).
4. **P1:** run separate Vehicle Health read-only probes for batterySupport, tyrePressure, vehicleHealthWarnings; 200 with missing/error job is not usable.
5. **P2:** investigate Audi Data Act separately with explicit consent, provider contracts and credentials; no automatic data-act fallback.
6. **Release gate:** unit tests + hassfest + HACS ZIP + on-car Q8 diagnostics + comparison to myAudi, before enabling periodic polling or claiming complete restoration.

**Installability is not live acceptance.** b14 is a test-only HACS prerelease; the user has installed it and has not yet produced diagnostics after the new trip-read or Vehicle Health actions.
