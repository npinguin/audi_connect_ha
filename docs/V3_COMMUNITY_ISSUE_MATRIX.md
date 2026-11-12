# V3 upstream issue validation

Source: [upstream PR #918](https://github.com/audiconnect/audi_connect_ha/pull/918) at `14f2b2b` and [development PR #22](https://github.com/npinguin/audi_connect_ha/pull/22).

These are validation candidates, not closed issues. Automated regressions do not prove physical vehicle behavior.

## Candidate coverage and acceptance

- [#907](https://github.com/audiconnect/audi_connect_ha/issues/907) — Trip archive, scoped snapshots, identity retry. **Acceptance:** All trip scopes and identity against myAudi; identity can remain absent.
- [#917](https://github.com/audiconnect/audi_connect_ha/issues/917) — Auxiliary-heating routing; restricted engine actions. **Acceptance:** Petrol A6 preheater start/stop; no unsupported engine or climate commands.
- [#914](https://github.com/audiconnect/audi_connect_ha/issues/914) — Auth-family routing and CARIAD command tests. **Acceptance:** A3 e-tron Auth0 climate on legacy API level; physical outcome.
- [#873](https://github.com/audiconnect/audi_connect_ha/issues/873) — Stored-settings climate start and variant selection. **Acceptance:** Q8 Sportback e-tron without settings; physical start/stop.
- [#871](https://github.com/audiconnect/audi_connect_ha/issues/871) — Parameterized climate and settings preservation. **Acceptance:** Legacy vehicle payload and physical outcome.
- [#865](https://github.com/audiconnect/audi_connect_ha/issues/865) — Command verdicts, journal and readback. **Acceptance:** US e-tron: accepted but unconfirmed charging must not claim success.
- [#875](https://github.com/audiconnect/audi_connect_ha/issues/875) — Pending/uncertain handling and fresh readback. **Acceptance:** Climate confirmation; no repeated mutation.
- [#861](https://github.com/audiconnect/audi_connect_ha/issues/861) — Access summary; unknown/stale states. **Acceptance:** Two-door A5 overall lock and partial-door state.
- [#888](https://github.com/audiconnect/audi_connect_ha/issues/888) — Position 404 recovery regression. **Acceptance:** Recovery after temporary parking 404.
- [#878](https://github.com/audiconnect/audi_connect_ha/issues/878) — Numeric sensor and Recorder tests. **Acceptance:** Statistics graph and retained entity IDs.
- [#880](https://github.com/audiconnect/audi_connect_ha/issues/880) — Cancellation and deadline regression. **Acceptance:** Cancellation in running HA.
- [#903](https://github.com/audiconnect/audi_connect_ha/issues/903) — Shared Auth0 account and family selection. **Acceptance:** EU/CA login and refresh; legacy limitations remain.
- [#913](https://github.com/audiconnect/audi_connect_ha/issues/913) — Shared auth flow; no specific fix claimed. **Acceptance:** Reproduce callback handling.
- [#879](https://github.com/audiconnect/audi_connect_ha/issues/879) — Shared authentication; no specific fix claimed. **Acceptance:** Password change and reauthentication.
- [#868](https://github.com/audiconnect/audi_connect_ha/issues/868) — Health, freshness, partial response evidence. **Acceptance:** Reproduce OEM inconsistency.
- [#862](https://github.com/audiconnect/audi_connect_ha/issues/862) — Preheater policy and command status. **Acceptance:** Reproduce original logging/error behavior.
- [#725](https://github.com/audiconnect/audi_connect_ha/issues/725) — Native charging and service compatibility. **Acceptance:** Historical stop-charger action on supported vehicle.
- [#881](https://github.com/audiconnect/audi_connect_ha/issues/881) — Documentation; outside runtime scope. **Acceptance:** Maintainer documentation review.

## Regression evidence

Relevant tests: `test_v3_trip_archive.py`, `test_v3_vehicle_identity.py`, `test_v3_climate_registry.py`, `test_v3_cariad_command_payloads.py`, `test_v3_legacy_context.py`, `test_v3_request_status.py`, `test_v3_b15_health_access.py`, `test_position_404_recovery.py`, `test_numeric_sensor_statistics.py`, `test_request_cancellation_regression.py` and `test_remote_confirmation_verdicts.py`.

For each live report record software versions, model/year/powertrain, market, expected and actual result, freshness, backend verdict and physical confirmation separately. Do not share raw Home Assistant diagnostics, credentials, VINs, private locations or trip data. Do not close upstream issues based on this matrix alone.
