# V3 feature closure and release acceptance

**Current decision: B41 development candidate; stable NO GO.** B40 remains the published test baseline. Issue [#44](https://github.com/npinguin/audi_connect_ha/issues/44) owns stable acceptance. This document records evidence and unresolved gates; [V3 review](V3_REVIEW.md) is the current user/engineering guide.

## Existing authoritative inventories

- [V2 parity baseline](V2_V3_PARITY_BASELINE.json): 109 historical entity slots, 9 platforms, 11 services, 11 execute-action choices and 19 control workstreams. The baseline is a historical snapshot, not a current generated inventory.
- [Product entity contract](../custom_components/audiconnect/v3/product_entities.json): native HA identities, metadata references and declared product extensions.
- [Capability catalog](../custom_components/audiconnect/v3/full_catalog.json): executable operation variants; applicability and evidence are separate.
- [Ownership](../governance/OWNERSHIP.json): responsibility and architecture constraints.

Do not reproduce these inventories in a second editable catalog. A declared row is not evidence that its implementation works on a real vehicle.

## B41 implementation and evidence

The B41 product-code head [3ff5263](https://github.com/npinguin/audi_connect_ha/commit/3ff5263e6388c6db996f05c1ce630abcba867448) passed [Test #1985](https://github.com/npinguin/audi_connect_ha/actions/runs/43622884825) (1,265 Python tests, 43 Workbench tests, lint) and [Validate #1986](https://github.com/npinguin/audi_connect_ha/actions/runs/43622884817). This is automated evidence for that exact head, not field acceptance. The documentation successor must pass its own exact-head checks before integration.

| Area | Implemented in B41 | Remaining evidence |
| --- | --- | --- |
| Operational switch state | Charging and window-heating switches no longer project unconfirmed requested On/Off as physical state. Last reported state and capture remain informational. | Q5 real charging STOP and START, stale/unknown UI and actual readback. |
| Entity continuity | Existing mapped read-only sensor/binary-sensor registry identities re-offered on reload without requiring a new reading; retired identities remain retired. | Q5 upgrade/restart and the five reported missing entities, Q8 regression, user-disabled settings. |
| Climate discovery | Catalog-driven Guided and Expert selective share reviewed action metadata, typed parameters, resolver and verification; read temperature independent of write support. | Q5 stored start, parameterized start, independent setpoint update and stop; Q8 stored start and read-only/write feature parity. |
| Extendability | Existing SOC operation can be added to discovery in a regression test through metadata alone; not enabled in the production catalog. | No extra product feature is required for B41. |
| Freshness | Existing B40 shared observation/readback writer retained; no new polling or command route. | Actual post-dispatch capture, full charge cycle, last-known versus not-applicable ETA and cross-source capture consistency. |

### Q5 field evidence — charging remains open

- [B35 physical test](https://github.com/audiconnect/audi_connect_ha/pull/918#issuecomment-6877274976): tester reports successful START and STOP on a 2020 Q5 55 TFSI e, independently confirmed by approximately 2 kW while charging and 4.4 W after STOP. Smart charging was enabled. 1,000 trips were retained.
- [B39 field report](https://github.com/audiconnect/audi_connect_ha/pull/918#issuecomment-6880663863): STOP accepted (HTTP 200) but the vehicle continued charging; HA sometimes showed Off. Five historical entities were reported as no longer provided. Stale data and missing ETA require explicit interpretation, not fabricated values.
- [B40 retest, 14 November 2026](https://github.com/audiconnect/audi_connect_ha/pull/918#issuecomment-6881591226): with the timer disabled, STOP at 18:22:08 CET returned HTTP 200/accepted_unconfirmed, but physical power remained approximately 2 kW. myAudi reported timeout E.PA.VCF.18. Last reported charging was true, captured at 18:20:26 CET, before dispatch. HA Off was optimistic. Two diagnostics and an error screenshot are available in the upstream comment.

B41 addresses the false state projection, not the physical STOP root cause. Do not attribute the failure to timers, a changed route or Audi alone without comparing the before/after diagnostics and actual B35/B40 execution evidence. Do not blindly retry or change endpoints. Confirm the physical result separately with vehicle/myAudi/power evidence. The attached diagnostics have not yet been analyzed in this documentation update.

### Remaining acceptance and release gates

| Gate | Required evidence |
| --- | --- |
| Q5 physical controls | Compare B35/B40 command evidence; B41 START/STOP with actual power, pending/last-known behavior; targeted climate tests. |
| Q8 physical regression | Stored-settings climate, stop, read target, lock/unlock; charging cycle including ETA expiry; no optimistic charging state. |
| Registry and trips | Previously mapped entities retained on reload and upgrade; retired Charging ready remains retired; no deletion of user choices or recorder history; 394 Q8 and 1,000 Q5 historical trip baselines remain intact where applicable. |
| Identity #35 | Actual OEM model/year and drivetrain evidence or explicit accepted limitation; GraphQL partial response is not proof of unsupported vehicle. |
| Data and lifecycle | Drive, sleep, charging, optional Data Act connect/disconnect/reconnect, restart and V2 rollback; timestamp and quota behavior over a representative period. |
| Broader scope #44 | Representative ICE/PHEV/BEV, Auth0/legacy and supported markets, legacy reads, services, all native platforms and actual controls; sharing/import, security and multi-account lifecycle. |
| Candidate packaging | Exact final-head Test/Validate, pinned dev source, both supported HA targets, archive/checksum and preceding published beta present in upstream review. |
| Upstream stable | Existing [PR #918](https://github.com/audiconnect/audi_connect_ha/pull/918), reviewed scope and maintainer acceptance. CI or a single vehicle does not close the stable gate. |

The original functional scope remains below. Historical behavior and earlier evidence are preserved at the pinned B40 source; the current B41 contract and the user guide take precedence. Feature freeze: only evidence-backed corrections, security fixes and documentation/acceptance closure. No V2/default-runtime change, new polling, speculative routes or release promotion on CI alone.

## Original functional scope (still in scope for #44)

| Area             | Gap / required evidence                                                                                                    |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Vehicle identity | OEM manufacturer model/year and image variants; real account evidence, restart and missing metadata behavior               |
| ICE/PHEV/BEV     | Representative vehicle evidence for applicable readings, controls and powertrain-specific projections                      |
| Trips            | CARIAD reset history not established; confirm MBB current/reset and CARIAD current/last, local archive and restart         |
| Legacy reads     | Verify actual MBB status, timers, preheater, vehicle data and unsupported modern equivalents                               |
| Charging         | Physical start/stop, manual/timer mode, target SOC, active and individual profile writes and readback                      |
| Climate          | Stored and parameterized start, stop, settings, windows, auxiliary duration; Auth0 and legacy acceptance                   |
| Access / remote  | Lock/unlock, flash, refresh/wake, engine start/stop where eligible; confirm actual outcome and fail-closed behavior        |
| HA lifecycle     | All nine native platforms, historical service contracts, user preferences, recorder history, restart and V2/V3/V2 rollback |
| Workbench        | Definition copy/paste exists; community sharing/import portability, roundtrip and redaction need explicit acceptance       |
| Operations       | Quota, expiry, partial responses, failed refresh, multi-account ownership, privacy and removal evidence                    |

## Historical evidence

The [pinned B40 feature-closure record](https://github.com/npinguin/audi_connect_ha/blob/b245cd62b51b08398166932dcb4f95987b87a4e9/docs/V3_FEATURE_CLOSURE.md) preserves the original baseline, B23–B40 engineering changes, measured field evidence and earlier release decisions. The [pinned B40 review](https://github.com/npinguin/audi_connect_ha/blob/b245cd62b51b08398166932dcb4f95987b87a4e9/docs/V3_REVIEW.md) preserves the B37–B40 review. Neither is a second active specification.
