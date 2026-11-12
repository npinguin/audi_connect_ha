# V3 upstream readiness — release and PR acceptance

**Decision: NO-GO for upstream release and normal completeness-qualified HACS release. One-time b13 experimental evidence-acquisition prerelease explicitly authorized.** Development branch: `feature/v3-clean-discovery`. Internal [draft PR #22](https://github.com/npinguin/audi_connect_ha/pull/22) targets `main`; it is not an upstream release PR. Published b12 stays immutable; b13 must pass exact-SHA CI and the [version-specific authorization](../governance/B13_EXPERIMENTAL_TEST_RELEASE.json). The machine-readable [completeness gate](../governance/V3_COMPLETENESS_GATE.json) remains authoritative; this document describes the work and evidence needed, not a gate override.

## 1. What the upstream community gets

V3 adds a capability-driven multi-generation Audi API runtime, native HA projection, improved freshness and guarded command execution, plus an optional Engineering Dashboard. Users connect and use eligible known capabilities; explorers discover gaps; engineers configure, test and locally activate supported routes, then contribute reusable evidence. See [community how-to](V3_COMMUNITY_HOWTO.md) and [proposed upstream README](V3_UPSTREAM_README.md).

Development after b12 includes a bounded private trip archive, complementary telemetry and structured details, native charging/window-heating switches, automatic reviewed read discovery and command/wake fixes. These are b13 candidate changes, not a physically certified feature list.

## 2. Remaining blockers — gate snapshot

At review on 2026-11-12: eight items closed at the recorded implementation/test level, seven implemented pending validation and one open live acceptance item. Closed implementation gates do not establish physical acceptance. [Recorded CI run](https://github.com/npinguin/audi_connect_ha/actions/runs/43227013194) supports the closure evidence in the gate; it is not proof of the latest PR head.

| Gate ID | Remaining work / exit evidence | Normal HACS completeness | Upstream |
| --- | --- | --- | --- |
| identity | Capture real localized manufacturer model/inventory and independent powertrain evidence; confirm no guessed labels, stable identity on missing inventory | Blocked | Blocked |
| trip_durable_history | Validate actual OEM endpoint coverage, overlapping/unsorted trips, deduplication, retention and restart; document limits of backfill; no lifetime-history claim | Blocked | Blocked |
| structured_details | Obtain remaining departureProfiles/timer/profile schema evidence; verify recurring/single timers, readiness and charging/battery-care semantics against real data; explicit disposition for unsupported/unobserved fields | Blocked | Blocked |
| health_details | Collect real Audi warning/campaign, inspection and low-voltage battery responses; validate supported semantics, no invented voltage or healthy state | Blocked | Blocked |
| discovery | Execute complete applicable reviewed read-only scan; account for all 23 shared jobs and reviewed standalone routes, record context/quota exclusions and unknowns; no automatic physical actions | Blocked | Blocked |
| schema_disposition | Capture fresh non-truncated per-job schema inventory or resolve remaining truncation; assign observed leaves to native state, normalized attribute, metadata or reviewed explicit unresolved/excluded disposition | Blocked | Blocked |
| upstream_matrix | Populate route/attribute/command evidence matrix with actual candidate evidence, vehicle/API/region applicability and exclusions; separate code, HTTP, schema, freshness, readback and physical proof | Blocked | Blocked |
| live_acceptance | Live candidate Q8 acceptance plus representative ICE/BEV and MBB evidence or explicit untested declaration; physical commands, setup, registry, Recorder and rollback | Separate live gate | Blocked |

Closed implementation gates: command_projection, operational_switches, trip_coverage, range_soc, oil_boolean, access_details, capability_details, registry_lifecycle. Reopen on regression. See [completeness audit](V3_COMPLETENESS_AUDIT.md), [takeover evidence](V3_COMPLETENESS_TAKEOVER.md) and the machine gate for details.

The installed b12 evidence is one vehicle only: 14/23 jobs observed; climate stored start/stop physically confirmed; parameterized climate start and unlock have HTTP evidence but not physical confirmation; wake HTTP 204 is not proof of vehicle wake. Do not transfer that evidence to the new candidate or other cars.

## 3. Engineering acceptance checklist before upstream promotion

- [ ] Close the seven evidence/disposition blockers with linked artifacts and regression coverage; update machine gate only when supported.
- [ ] Reconcile latest official upstream master and merged PRs #915/#916 against the fork V2 delta register and V2/V3 parity baseline. Avoid duplicate contributions; preserve upstream V2 behavior, domain, services, IDs, translations and HACS conventions.
- [ ] Complete semantic parity review: every historical entity, service, source mapping and control has a supported implementation, intentional migration, or explicit reviewed limitation. Check declared catalog counts against generated inventories.
- [ ] Validate clean setup and warm restart in normal user mode without Workbench interaction or physical discovery mutations; exercise unknown/stale/partial/error states and multi-car isolation.
- [ ] Validate engineering workflow: read-only scan, custom local sensor/route draft, verified mapping activation, exact-action consent, supported alternative control activation and privacy-safe contribution. Document unsupported custom parameterized/PUT semantics, not arbitrary raw command execution.
- [ ] Verify persistent command lifecycle, backend acceptance versus actual readback, cancellation/restart/uncertainty, stop behavior, 10-second normal cooldown and separate engineering guard; no speculative retries; verify auth serialization and quota recovery. Review transport allowlist, S-PIN handling and diagnostics redaction.
- [ ] Review module ownership, dependency boundaries, typed contracts, risk-based coverage and remaining architecture closure items; avoid duplicate runtimes/dispatchers.
- [ ] Execute full candidate CI at the exact release SHA (Python and frontend regression tests, hassfest, HACS validation, release metadata/package checks and applicable architecture/parity guards). Record links and results, not only a test count.
- [ ] Complete clean install, V2→V3 upgrade, reload/restart, multi-vehicle lifecycle and V3→V2 runtime rollback on real HA. Verify existing device/entity IDs, history/Recorder, user names and disabled state, existing automations and account settings. Test package downgrade with backup/restore separately.
- [ ] Verify actual vehicle behavior with representative supported contexts (Q8 PHEV/Auth0, applicable ICE, BEV, legacy MBB; region/permissions as relevant). Physically verify eligible climate/charge/window heating/access/remote actions individually when safe; mark unavailable/not applicable/untested accurately. Do not claim untested model or regional coverage.
- [ ] Attach public-safe evidence matrix, known limitations, compatibility/upgrade/rollback guide, release notes, user/explorer/engineer how-to and upstream README. Review redaction manually; no VIN, secrets, private trip/position data or raw personal payloads.
- [ ] Obtain explicit maintainer acceptance of scope, unresolved limitations and delivery sequence before any upstream merge or release.

The [test matrix](V3_TEST_MATRIX.md), [architecture closure](V3_ARCHITECTURE_CLOSURE.md), [implementation progress](V3_CLOSURE_IMPLEMENTATION.md) and [ADR 002](V3_ADR_002_FAST_DISCOVERY.md) remain the detailed acceptance references.

## 4. Proposed delivery sequence (not release authorization)

1. **Internal draft PR #22:** retain draft/NO-GO while completing implementation/evidence and exact-head CI; no merge or publication from this document.
2. **Next immutable HACS test candidate:** only after the completeness gate permits it, with explicit scope, exact-SHA validation, versioned release artifacts and a documented physical acceptance plan. Keep V2 default/fallback until separately approved. The normal gate requires fresh target evidence. The sole b13 exception is explicitly authorized to acquire that evidence on the improved build; no gate is marked closed and no further exception is implied.
3. **Community acceptance:** supervised candidate tests, privacy-safe model/API compatibility matrix, migration/rollback and regression closure. No physical actions during discovery.
4. **Upstream review:** agree scope and review strategy with maintainers. Prefer reviewable changes (shared compatibility/reliability deltas, V3 runtime/catalog and HA projection, Workbench/diagnostics, docs/tests) if they can be independently integrated without breaking dependencies; otherwise use a coherent reviewed implementation PR. Do not create persistent parallel dev branches or duplicate already merged upstream work.
5. **Official release:** only after upstream acceptance, exact release verification and explicit maintainer release approval. Decide default-runtime policy explicitly with upstream; do not silently switch all users to V3.

This is a proposed PR/release sequence, not a commitment from upstream. Automatic contribution export/import remains a proposed enhancement rather than a current release capability or an added mandatory gate.

## 5. Evidence record for each release candidate

Record candidate SHA, tag/version, CI URLs/results, HA version, model/year/powertrain, region, API/auth family, capability and operation revision, implementation result, automated test result, HTTP outcome, schema validation, capture freshness, readback, physical result, migration/rollback outcome, exclusions and reviewer. Use separate statuses for unobserved, not applicable, blocked, failed and not tested. No personally identifying vehicle or account data.

**Definition of done:** both machine gates are true with linked evidence, exact-SHA checks are green, real HA/vehicle acceptance and rollback are documented, and upstream maintainers have agreed on the actual release scope. A draft PR, passing synthetic CI or HTTP success alone cannot satisfy this definition.


## Post-b13 work

[b13](https://github.com/npinguin/audi_connect_ha/releases/tag/3.0.0b13) was published as a one-time evidence-acquisition prerelease after [exact-SHA CI](https://github.com/npinguin/audi_connect_ha/actions/runs/43228317523). No pending evidence gate was closed. See [upstream reconciliation](V3_UPSTREAM_RECONCILIATION.md) for the exact dev/master comparison including already merged PRs #915/#916. New changes after b13 are development only. Expanded diagnostics capture standalone schemas, preserve multiple observed schema variants within a session, report discovery progress and bounded trip archive completeness indicators; partial trip duplicates merge only on a unique compatible odometer interval. Physical and cross-model evidence remain outstanding.
