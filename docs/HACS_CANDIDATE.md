# Audi Connect 3.0.0b39 — capability consolidation candidate

Experimental HACS prerelease. V2 remains the default and rollback; V3 is opt-in and Data Act is disabled by default. This is not a stable release.

## Changes since B38

- One consolidated capability view with source priority, mapping and observation evidence, selected source, capture/receipt/delivery timestamps and the distinction between missing mappings, missing values and invalid values.
- 47 additional read-only engineering fields grouped by capability; two technical source fields remain in API evidence. No new Home Assistant entities or polling requests.
- Explicit operational versus engineering-only freshness; invalid newer Data Act observations withdraw earlier values for that source while independent valid native values remain available.
- Vehicle-scoped Data Act health, validation of declared mappings, read-only Workbench status projection and reuse of trip observation evidence. Local custom attribute identifiers and private values remain excluded from public diagnostics.
- Q8 B38 baseline: 64 of 101 canonical attributes normalized, no fresh canonical observations; 394 trip records retained. The candidate improves visibility and handling, not OEM data availability or proven vehicle support.
- PR #54 exact head: 1,248 Python tests passed; Workbench, lint, HACS, hassfest and semantic title checks passed. Candidate workflow rechecks both supported HA targets and the packaged archive.

## Field acceptance

Back up Home Assistant, upgrade from B38 without deleting the integration or devices, and restart. Keep the existing runtime and credentials. Check the capability view, source priority and fallback, timestamps after driving/charging, Data Act connection/withdrawal, entity IDs and trip history. Report regressions and sanitized evidence only. OEM model/year/drivetrain, live Q8 freshness and control coverage remain open; no speculative mappings or stable promotion. Issue #44 remains the stable gate.

Source: merged PR #54, 08b44f4bb4fa3f4a87274328d7c93aea6c6a9b0d.
