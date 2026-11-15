# Audi Connect 3.0.0b43 — reliability & continuity test beta

Experimental HACS prerelease, authorized for community testing. V2 remains the default and fallback; V3 is opt-in. EU Data Act remains optional. This is not stable promotion.

## Improvements since B42

- Preserve newer native last-known readings, including SoC, across partial/invalid responses and restart. Show the actual measurement provenance; historical data is not fresh command evidence.
- Charging START/STOP reflects reported vehicle state rather than an assumed successful action. HTTP acceptance, backend completion and actual observations remain separate. Preserve received HTTP evidence even if later local processing fails.
- Preserve physically verified discovery and independently verified charge modes across restart and routine command failures. Bind reviews to their operation revision; a failed timer test does not withdraw independent manual-mode proof.
- Consolidate request budgets, native priorities and recovery. Respect Retry-After, use bounded fallback for repeated throttling, avoid unnecessary optional reads, prioritize native status, rotate vehicles fairly, and preserve the complete necessary command request allowance, including legacy access preparation.
- Keep configured native cadence; deferred reads are not cloud failures. Data Act normal delivery checks remain 30 minutes and back off to 60 minutes when idle; recover from valid empty delivery without retaining stale throttling.
- Validate conflicting temperature inputs before settings reads. Preserve existing routes, vehicle/entity IDs, trip history and normal HA controls. Workbench displays distinct historical HA projection provenance.
- Simplified onboarding and engineering documentation. No new runtime files, API routes, schedulers or entity definitions.

## Installation and field acceptance

Back up HA. In HACS enable beta versions, select 3.0.0b43, update and restart without deleting the integration or its devices. Test existing proven controls first, then use Vehicle Setup & Discovery only where needed.

Check native charging against measured power, actual START/STOP, manual/timer modes, climate and access, sleep/restart, retained trips and entity IDs, timestamps and quota with more than one client. Test EU Data Act separately. Export sanitized diagnostics when reporting a problem.

The physical Q5 STOP regression, exact Q6 charge-target schema, manufacturer identity, auxiliary heating, Q4 partial-response/parking behavior and real multi-client quota scope still need field evidence. HTTP acceptance is not physical execution. Ownership consolidation findings remain documented; no speculative redesign or stable claim.

Source: merged PR #60, 35314ae4c5986a02efdfdb253090a10af5265492. Exact product head 1f17aab476dd1d12ecc7b5f2e486376a4cf37a2f passed 1,329 Python tests on HA 2026.11.1, 43 Workbench tests, lint, HACS and hassfest (Test #2187, Validate #2188). The release workflow independently verifies the pinned source and tests only the latest stable monthly HA release, then checks archive integrity and SHA256. Older HA support metadata is unchanged, not newly revalidated. Stable gate #44 remains open. Upstream #918 remains on B42 pending separate review synchronization.
