# Audi Connect 3.0.0b36 — experimental fix and finish

Experimental fork HACS prerelease for live acceptance. V2 remains the default and fallback, V3 is opt-in, and EU Data Act remains disabled by default. Not a stable or upstream release.

## Changes since B35

- Normalize implausible vehicle timestamps at receipt; they can never age into valid evidence. Historical charging profiles, timers and capability fallback use the same capture validity policy.
- Native command readback requires a valid capture and observation received after the command started; use the existing catalog family priorities. No new command routes or automatic retries.
- Parking hints no longer appear as current vehicle motion. Last-known parked location remains intact.
- Missing Data Act subscription is now actionable and removes that channel's current readings, without erasing valid native data.
- No new runtime modules, entity IDs, requests, polling tasks, persistent state or configuration. RHI consumers need no migration; motion without evidence is intentionally unknown.

PR #50 exact head passed 1,232 Python tests, Workbench, pre-commit, HACS and hassfest. The merged dev tree is identical. B35 product source is offered through existing upstream PR #918. Candidate publication requires both supported HA versions and archive verification.

## Live acceptance

Back up HA; retain the existing entry and entity registry. Install the beta, keep V3 selected, and check Integration status, vehicle captures, charging readiness and physical command results. Test optional Data Act only with an existing authorized portal subscription. Verify restart, native status isolation and rollback. Share redacted integration diagnostics, not raw VINs, credentials, locations or payloads. Manufacturer metadata, complete model/market acceptance and physical command evidence remain open; issue #44 is not closed.

Source: merged PR #50, 1a297db8f760f4c3244cbdd7f16f6fc38e62a573.
