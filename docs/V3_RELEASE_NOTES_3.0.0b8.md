# Audi Connect 3.0.0b8 — V3 architecture, reliability & parked-car telemetry (experimental HACS test)

**Release class:** Explicit maintainer-requested experimental HACS test prerelease. **NOT full V2 parity, NOT code-complete, NOT stable.** This one-time authorization does not change normal publication or stable-promotion gates.

This package uses the **existing Audi Connect config entry** and keeps V2 available through the runtime selector. V2 remains a fallback; its 33 upstream/shared file deltas are recorded for review. V3 is a separate implementation with shared bootstrap/authentication and configuration. No second integration or account setup is required. Switching V2↔V3 still reloads the HA config entry; it is not a no-downtime process.

## Fixed since b7

- **Entity registry:** V3 no longer mass-disables registered V2 entities during an experimental runtime switch. Prior integration-owned hidden entries are restored; the user's own disabled entries are never re-enabled. The Q8 b7 diagnostics had 90 entities, 59 integration-disabled in V3 vs zero disabled in V2.
- **Parked vehicle telemetry:** previously observed CARIAD read jobs remain polled after discovery; out-of-order captured timestamps no longer overwrite newer vehicle values. Readings such as SoC, range, mileage and maintenance may show **last-known stale** values, while charging, climate activity and safety statuses require recent evidence.
- **One Audi account owner:** when V3 is selected the existing `AudiAccount` authentication/service instance owns the refresh token and OAuth tokens. V3 continues to own **independent** vehicle discovery, GET/POST execution, response parsing and the one active data coordinator. No V2 business poll runs in parallel.
- **HA services:** all existing `audiconnect.*` service identifiers are registered in both runtimes. V3 routes the currently verified climate, charging, access and window-heating actions through its own guarded engine. **Unmigrated options/actions return a clear Home Assistant error**, never a hidden V2 operation or speculative OEM POST. Vehicle wake, cloud refresh and data read are intentionally distinct.
- **Guided control discovery:** read-only discovery remains automatic; non-S-PIN and S-PIN controls have separate candidate groups and exact-action consent. Only one command is authorized at a time, settings PUTs accept explicit parameters, and physical results are reviewed before activation. No new HA probe services or automatic command tests.
- **V3 device presentation:** 15 historical V2 sensor contracts that were tagged diagnostic are displayed under ordinary Sensors **in V3 only**. Upstream V2's existing platform metadata is not modified. Technical integration health remains in Diagnostics.
- **Governance:** new exhaustive V2/V3 source parity matrix and machine-readable baseline: 109 historical V2 source entity slots across nine HA platforms, 110 source field references, 72 sensor metadata contracts, 11 HA service IDs and 19 control workstreams; CI tests detect drift.

## Architecture and reliability closure in this build

- Independent status and command engines, generic scheduled capability status planning, and dynamic HA entity projection across all nine platforms.
- Serialized authentication and profile writes, bounded read-only quota recovery, and per-vehicle control matching with versioned route evidence.
- Persisted normal command context before mutation; no automatic replay after uncertainty, request-ID persistence, cooldown, and fresh post-command readback for known stateful commands.
- Removed obsolete V3 climate pilot and inherited coordinator from production; original config-entry selector and entity identities remain.
- Inventory reconciliation preserves existing entity identities, blocks excluded or repeatedly missing vehicles, and supports rediscovery.
- Pinned V2 upstream delta register and module ownership. Full static/live parity, generic custom parameterized commands/PUT and unified command history remain open.

## Current parity status

- Independent MBB reads, climate start/stop, S-PIN challenge-response lock/unlock, bounded backend confirmation, region selection and legacy trip data are implemented. Explicitly reviewed legacy-bearer CARIAD routes are supported without V2 business fallback.
- Historical access, charge profiles/timers, outdoor temperature, parking, trip data, and native HA controls now have independent source-backed paths. The matrix includes the fixbranch's additional last-trip sensor.
- Remaining implementation/verification gaps: legacy timer interpretation, modern reset-history availability and actual HA entity behavior. The current matrix is not a static-parity sign-off.
- All four temporary probe services are intentionally excluded. No automatic mutating discovery.
- Physical Q8 command acceptance, recorder repair and runtime rollback are required after the test package is published, before stable promotion.

## Installation / safe test

1. Keep the existing working **V2** selected unless testing V3 intentionally.
2. Back up Home Assistant (configuration, entity registry and recorder). In HACS, open Audi Connect from `npinguin/audi_connect_ha`, select Redownload / Show beta versions and choose `3.0.0b8`. Restart HA and initially keep V2 selected. Switch to V3 only for supervised testing.
3. Confirm the **same Audi device and existing entity IDs** remain in HA before and after switching the runtime option.
4. In V3, observe SoC, range, mileage and maintenance data while parked for over 60 minutes. Check `vehicle_freshness`/`stale_last_known` and avoid interpreting old active status as live.
5. Do not test physical lock, climate, wake or charging commands unless present at the vehicle and the V3 Workbench route has been explicitly verified. An HTTP 2xx means **accepted, not physically completed**.
6. For missing functionality, switch runtime to V2; no re-pairing is expected.

## Engineering quality gate

Normal prerelease publication still requires manual dispatch, static parity and code-completeness sign-off. This one-time b8 experimental HACS test exception requires exact version-bound authorization and successful full CI on the release commit. It is a prerelease, never latest/stable. No existing tag or ZIP may be replaced. Physical acceptance and rollback remain separate stable gates.

**No real-car acceptance is implied by CI.** Compare [V2/V3 parity matrix](V2_V3_PARITY_MATRIX.md), [machine-readable baseline](V2_V3_PARITY_BASELINE.json), and [shared account & HA identity ADR](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md).
