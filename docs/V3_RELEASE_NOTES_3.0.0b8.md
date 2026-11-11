# Audi Connect 3.0.0b8 — V2-compatible identity & parked-car telemetry (experimental)

**Release class:** HACS/GitHub prerelease for controlled testing. **NOT full V2 parity.**

This package uses the **existing Audi Connect config entry** and keeps V2 available through the runtime selector. No second integration or account setup is required. Switching V2↔V3 still reloads the HA config entry; it is not a no-downtime process.

## Fixed since b7

- **Entity registry:** V3 no longer mass-disables registered V2 entities during an experimental runtime switch. Prior integration-owned hidden entries are restored; the user's own disabled entries are never re-enabled. The Q8 b7 diagnostics had 90 entities, 59 integration-disabled in V3 vs zero disabled in V2.
- **Parked vehicle telemetry:** previously observed CARIAD read jobs remain polled after discovery; out-of-order captured timestamps no longer overwrite newer vehicle values. Readings such as SoC, range, mileage and maintenance may show **last-known stale** values, while charging, climate activity and safety statuses require recent evidence.
- **One Audi account owner:** when V3 is selected the existing `AudiAccount` authentication/service instance owns the refresh token and OAuth tokens. V3 continues to own **independent** vehicle discovery, GET/POST execution, response parsing and the one active data coordinator. No V2 business poll runs in parallel.
- **HA services:** all existing `audiconnect.*` service identifiers are registered in both runtimes. V3 routes the currently verified climate, charging, access and window-heating actions through its own guarded engine. **Unmigrated options/actions return a clear Home Assistant error**, never a hidden V2 operation or speculative OEM POST. Vehicle wake, cloud refresh and data read are intentionally distinct.
- **Device presentation:** 15 vehicle telemetry sensors and 11 car-status binary sensors move out of HA Diagnostics into normal Sensors/Binary Sensors without any entity/unique-ID rename. Technical API, synchronization and quota health remains in Diagnostics.
- **Governance:** new exhaustive V2/V3 source parity matrix and machine-readable baseline: 109 historical V2 source entity slots across nine HA platforms, 110 source field references, 72 sensor metadata contracts, 12 HA service IDs and 20 control workstreams; CI tests detect drift.

## Still missing before full V2 parity

- Three HA platforms are not yet implemented in independent V3: native `number`, `select`, and `device_tracker`. V3 has limited read-only/derived sensor coverage. An entity may remain `unavailable` if V3 cannot yet provide its underlying value.
- The Q8's climate status was observed as `invalid` and no successful physical climate/start/stop/wake/lock end-to-end result has been established.
- Global and location-specific charge targets, charge mode, timers, preheater/auxiliary heating, remote flash and engine controls need safe V3 routing, metadata and vehicle-specific confirmation. Their old HA service names exist; they **must not be considered functional in V3** yet.
- V3 request-ID/pendingrequests tracking and physical readback, legacy MBB control parity, all 13 Recorder metadata repairs, vehicle-specific dynamic entities, and V2→V3→V2 rollback on a live HA installation remain open.
- New Media / Trips API expansion remains out of scope until V2 parity is accepted.

## Installation / safe test

1. Keep the existing working **V2** selected unless testing V3 intentionally.
2. Install this **prerelease** using HACS beta/prerelease selection where available, or download the integration-only ZIP and copy `audiconnect/` into `custom_components/`. Restart HA.
3. Confirm the **same Audi device and existing entity IDs** remain in HA before and after switching the runtime option.
4. In V3, observe SoC, range, mileage and maintenance data while parked for over 60 minutes. Check `vehicle_freshness`/`stale_last_known` and avoid interpreting old active status as live.
5. Do not test physical lock, climate, wake or charging commands unless present at the vehicle and the V3 Workbench route has been explicitly verified. An HTTP 2xx means **accepted, not physically completed**.
6. For missing functionality, switch runtime to V2; no re-pairing is expected.

## Engineering quality gate

Prerelease publication is controlled by `.github/workflows/v3-beta-release.yml`. It compiles, runs Python and Workbench regression tests, hassfest and HACS validation, and packages `custom_components/audiconnect` only. The tag and ZIP are immutable and use the exact tested SHA.

**No real-car acceptance is implied by CI.** Compare [V2/V3 parity matrix](V2_V3_PARITY_MATRIX.md), [machine-readable baseline](V2_V3_PARITY_BASELINE.json), and [shared account & HA identity ADR](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md).
