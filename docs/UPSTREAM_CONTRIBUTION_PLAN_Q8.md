# Upstream contribution plan — after Q8 live acceptance

Target: https://github.com/audiconnect/audi_connect_ha (default master).
Our fork: https://github.com/npinguin/audi_connect_ha

**Principle**: propose small, product-neutral, test-backed upstream PRs from a
fresh branch based on *current upstream master*; do not propose a blind merge
of Robotix's feature branch. Keep local dealer fields, user-specific HAR, debug
token samples and RHI Mobility details OUT of upstream changes.

## Candidate PR 1 — read-only stability
Portable scope:
- Detect CARIAD HTTP 200 containing failed jobs, preserving previously valid
  states without pretending the old car timestamp is new.
- Capability-aware selective-status planner with first-poll/unknown fallback,
  stable job ordering and zero additional HTTP calls.
- Model longName -> shortName -> clearly labeled nickname fallback.
- ParkingPosition capture time as *estimated* Park Time when the old parking
  clock isn't returned, reusing the original unique IDs.
- Precise tests for partial outage, timestamps, capabilities and model.

Evidence: Q8 PHEV + upstream issues #907, #687 and #793/#854.
No sensitive values; tests contain synthetic VIN only.

## Candidate PR 2 — modern CARIAD remote actions (after physical validation)
Portable scope:
- Auth0 uses modern CARIAD /access/lock and /access/unlock with local Audi S-PIN;
  legacy login keeps its previous RLU handling.
- Climate start/stop uses modern CARIAD API; explicit bodyless start (using
  car-stored settings) supported when equipment rejects partial settings.
- Preserve existing remote action entity IDs and HA service names.
- Remove silent False success and duplicated post-command refreshes.
- Treat HTTP 200/202/204 as gateway acknowledgement until car confirms action.
- Precise category-only HTTP command log; never VIN, bearer, S-PIN, raw body.
- Tests for physical-state semantics, rejected lock, climate and rate limits.

**Blocker**: Q8 LOCK still does NOT physically work; do not claim full
lock/unlock success upstream until the underlying rejection is understood.
Upstream can evaluate a clearly experimental permission-gated lock change,
but do not submit it as a complete fix based on HTTP 200.

Evidence: owner confirmed climate start/stop, unlock and flash in b5.
Relevant issues: #903, #873, #861.

## Candidate PR 3 — read-only climate timer support
Portable scope:
- Map climatisationTimersStatus.value.timers to bounded HA sensors, with
  explicit car-local-time semantics and no invented timezone/coordinates.
- Keep new IDs additive and expose only supported fields.
- Add synthetic fixtures for recurring and one-time timer cases.
- No default timer writes or background data probes.

## Handover and upstream gate
1. Install the integrated b7 beta in HA and run the 8-point real-car acceptance
   gate in docs/Q8_B7_COMPREHENSIVE_RELEASE.md.
2. Record physical commands outcome separately from HTTP status; verify
   functional regressions did not occur.
3. Diff candidate patches against the upstream master HEAD; eliminate
   overlapping upstream commits before opening PRs.
4. Create a separate minimal upstream-facing branch per PR; run upstream CI
   and Home Assistant hassfest, attach anonymized evidence and link issues.
5. Open a draft upstream PR with technical acceptance criteria and known
   limitations. Do not submit owner data, credentials, local dealer info,
   raw HAR, vehicle identifiers or GPS.
6. Iterate based on maintainer feedback, not on a sequence of unreviewed
   beta releases.

Do not advertise an untested command endpoint as an upstream fix.
