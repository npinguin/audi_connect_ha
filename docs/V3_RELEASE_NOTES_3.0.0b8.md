# Audi Connect 3.0.0b8 — V2-compatible identity & parked-car telemetry (experimental)

**Release class:** PREPARATION ONLY: not approved for publication until V2 parity is complete. **NOT full V2 parity.**

This package uses the **existing Audi Connect config entry** and keeps V2 available through the runtime selector. Upstream V2 business code is unchanged; V3 is a separate implementation, sharing only bootstrap/authentication and configuration. No second integration or account setup is required. Switching V2↔V3 still reloads the HA config entry; it is not a no-downtime process.

## Fixed since b7

- **Entity registry:** V3 no longer mass-disables registered V2 entities during an experimental runtime switch. Prior integration-owned hidden entries are restored; the user's own disabled entries are never re-enabled. The Q8 b7 diagnostics had 90 entities, 59 integration-disabled in V3 vs zero disabled in V2.
- **Parked vehicle telemetry:** previously observed CARIAD read jobs remain polled after discovery; out-of-order captured timestamps no longer overwrite newer vehicle values. Readings such as SoC, range, mileage and maintenance may show **last-known stale** values, while charging, climate activity and safety statuses require recent evidence.
- **One Audi account owner:** when V3 is selected the existing `AudiAccount` authentication/service instance owns the refresh token and OAuth tokens. V3 continues to own **independent** vehicle discovery, GET/POST execution, response parsing and the one active data coordinator. No V2 business poll runs in parallel.
- **HA services:** all existing `audiconnect.*` service identifiers are registered in both runtimes. V3 routes the currently verified climate, charging, access and window-heating actions through its own guarded engine. **Unmigrated options/actions return a clear Home Assistant error**, never a hidden V2 operation or speculative OEM POST. Vehicle wake, cloud refresh and data read are intentionally distinct.
- **Guided control discovery:** read-only discovery remains automatic; non-S-PIN and S-PIN controls have separate candidate groups and exact-action consent. Only one command is authorized at a time, settings PUTs accept explicit parameters, and physical results are reviewed before activation. No new HA probe services or automatic command tests.
- **V3 device presentation:** 15 historical V2 sensor contracts that were tagged diagnostic are displayed under ordinary Sensors **in V3 only**. Upstream V2's existing platform metadata is not modified. Technical integration health remains in Diagnostics.
- **Governance:** new exhaustive V2/V3 source parity matrix and machine-readable baseline: 109 historical V2 source entity slots across nine HA platforms, 110 source field references, 72 sensor metadata contracts, 11 HA service IDs and 19 control workstreams; CI tests detect drift.

## Current parity status

- Independent MBB reads, climate start/stop, S-PIN challenge-response lock/unlock, bounded backend confirmation, region selection and legacy trip data are implemented. Explicitly reviewed legacy-bearer CARIAD routes are supported without V2 business fallback.
- Historical access, charge profiles/timers, outdoor temperature, parking, trip data, and native HA controls now have independent source-backed paths. The matrix includes the fixbranch's additional last-trip sensor.
- Remaining implementation/verification gaps: quota restore display after HA restart, legacy timer interpretation, modern reset-history availability and actual HA entity behavior. The current matrix is not a static-parity sign-off.
- All four temporary probe services are intentionally excluded. No automatic mutating discovery.
- Physical Q8 command acceptance, recorder repair and runtime rollback are required after the test package is published, before stable promotion.

## Installation / safe test

1. Keep the existing working **V2** selected unless testing V3 intentionally.
2. **Do not install a b8 prerelease yet:** this is an unreleased draft and publishing is blocked until the V2 parity sign-off. Continue using the already working V2.
3. Confirm the **same Audi device and existing entity IDs** remain in HA before and after switching the runtime option.
4. In V3, observe SoC, range, mileage and maintenance data while parked for over 60 minutes. Check `vehicle_freshness`/`stale_last_known` and avoid interpreting old active status as live.
5. Do not test physical lock, climate, wake or charging commands unless present at the vehicle and the V3 Workbench route has been explicitly verified. An HTTP 2xx means **accepted, not physically completed**.
6. For missing functionality, switch runtime to V2; no re-pairing is expected.

## Engineering quality gate

Prerelease publication is blocked by `.github/workflows/v3-beta-release.yml` until an explicit manual dispatch and the test-release code-completeness sign-off and CI pass; physical acceptance is a separate stable gate. Routine pushes can run tests but cannot publish a tag or overwrite an existing ZIP.

**No real-car acceptance is implied by CI.** Compare [V2/V3 parity matrix](V2_V3_PARITY_MATRIX.md), [machine-readable baseline](V2_V3_PARITY_BASELINE.json), and [shared account & HA identity ADR](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md).
