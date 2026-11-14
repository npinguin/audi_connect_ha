# Audi Connect 3.0.0b40 — final stabilization test candidate

Experimental HACS prerelease. V2 remains the default and rollback; V3 is opt-in and Data Act is off by default. This is the final planned test candidate before live acceptance, not a stable release.

## Changes since B39

- Native polls and eligible command-response telemetry share the observation writer and capture projection. Valid post-command vehicle captures update entities and the existing last-update/age projection immediately, with actual operation provenance. Request echoes, missing or old capture timestamps and HTTP acceptance do not create fresh data or physical confirmation. No extra polling.
- Common bounded command projection window, independent of dispatch cooldown. Lock transitions remain conservative; newer reported state wins and contrary native readback remains a mismatch, not proof of failed physical execution. Expose requested state, command timestamps and optimistic versus reported state.
- Suppress derived charging ETA superseded by newer explicit non-charging status, preserve underlying duration for evidence. Invalid climate status no longer reports a valid climate age.
- Explicit latest and oldest vehicle capture ages in existing projections, with derived values identified separately from received source observations. Bounded privacy-safe capture evidence for core charging, access and climate attributes.
- EU Data Act connection status in options and the dedicated diagnostic; keep existing connection without reauthentication. Identity-only findings remain engineering evidence when native polling succeeds.
- Position uses the ordinary entity category. Redundant V3-only Charging ready retired through existing registry lifecycle; chargingState and history retained. Discovery assessment label distinguishes completed assessment from semantic data coverage.
- Updated user instructions, ownership and feature closure, final acceptance checklist. No new runtime owner, persistent cache, provider, request or speculative mapping.

## B39 Q8 field baseline

Five poll attempts, 15 native transport requests in the runtime, 394 archived trip records. 65/101 normalized canonical attributes (48 fresh, 17 stale); 3 invalid, 17 not observed, 14 not tested and 2 mapping pending. Latest valid capture 29 min, oldest 2491 min; access and charging renewed. Optional dataset received but its selected readings were not fresh. Latest unlock HTTP 200 followed by readback mismatch. Raw vehicle data and credentials are not in the repository.

## Field acceptance

Back up HA, install this candidate without deleting the integration or devices, restart and keep existing credentials. Verify entity IDs/history, Data Act connection/keep/disconnect/reconnect, ordinary diagnostics and Position, actual charge state and ETA after normal charge/drive, lock and climate command feedback and source timestamps, source matrix and V2 rollback. No unnecessary wake or repeated commands. See [the final acceptance checklist](docs/V3_REVIEW.md#b40-final-field-acceptance-before-stable-promotion). Upstream review #918 and stable gate #44 remain open; identity #35, physical charging and climate acceptance, broader representative vehicle coverage are not resolved by CI. Freeze feature scope after acceptance; no stable promotion on CI alone.

Source: merged PR #56, b245cd62b51b08398166932dcb4f95987b87a4e9; PR #55 is included. Exact-head Test/Validate and semantic title passed; 1,257 Python and 42 Workbench tests passed. Candidate workflow rechecks both HA compatibility targets and packaged archive.
