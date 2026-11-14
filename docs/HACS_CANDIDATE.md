# Audi Connect 3.0.0b37 — multi-source engineering closure

Experimental fork HACS prerelease for live acceptance. V2 remains default and fallback, V3 opt-in, and Data Act disabled by default. Not a stable or upstream release.

## Changes since B36

- Consolidated, registry-driven source discovery and Workbench coverage, including selected versus alternative source evidence, timestamps, and privacy-safe identity outcomes. Parking hints no longer count as normalized movement.
- Separate optional portal connect/reconnect/disconnect options; credentials validated before replacement. Existing native login unaffected.
- Withdraw source-specific readings and identity on terminal loss of portal access. Missing subscription is distinct. Preserve native measurements, trips and registry IDs.
- Invalidate current and cached observations on mapping changes; reject late disabled-route responses. Charging ETA follows the selected duration. Coalesce registry notifications.
- Share bounded response-body reading; use private HA storage for profiles and registry migration. Three exact read-only candidate mappings for charging/climate duration and hood status. No new controls, polling engine, scheduler or entity IDs.
- Exact PR #51 source passed 1,237 Python regression tests and pre-commit / Validate. Both supported HA versions and archive verification are required by the candidate workflow.

## Live acceptance

Back up HA, install over B36 without deleting the entry or devices, restart, retain V3 mode and existing portal credentials. Check source discovery, vehicle freshness, optional source delivery, identity and entity registry/trip history. Validate after a normal ride and while charging, then test physical controls with explicit consent. Check reconnect/disconnect only if needed; rollback to V2 remains available. No claim of fresh OEM telemetry, solved manufacturer identity, verified charging control or complete market coverage. Issue #44 remains the stable release gate. Share redacted diagnostics only.

Source: merged PR #51, adce2dd09f93ab8aced6be1f8ddf9a884f6f5938.
