# Audi Connect 3.0.0b32 — experimental EU Data Act and source consolidation

Experimental fork prerelease for real-vehicle validation, not a stable or upstream release. V2 remains default and fallback; V3 is opt-in, and the EU Data Act provider is disabled by default.

- Central family priority, deterministic observation selection including aging, one shared observation writer, passive native discovery, optional authentication isolation and bounded inventory fallback.
- Optional EU Data Act portal read session via existing integration options. Requires an existing authorized continuous Data Act request; no consent creation. Separate quota, 30-minute initial polling interval, nonblocking native publication and VIN-scoped denial.
- Nineteen mapped semantic attributes from the actual Q8 dataset schema, preserving existing HA entity IDs, field-level capture time, cloud observation, delivery and family provenance. No fabricated fresh data. Actual owner dataset not committed.
- Data Act never grants command permission or confirms a physical command. Lower-priority stale reads cannot supersede fresh higher-priority data; invalidation and revocation are family-scoped.
- Corrected historical alias projection and aggregate capture provenance. Exact-head PR #41 passed Test and Validate (1,189 Python tests), with full package matrix required by this workflow.

## Live acceptance

Enable V3 and then EU Data Act in the integration options only after ensuring your existing portal request works. Leave optional email/password blank to reuse stored myAudi credentials if available; use an independently authorized portal account when necessary. Do not share credentials in diagnostics or GitHub. Check source and actual vehicle capture times, native request counts, registry identity, failure isolation, restart/disable behavior and unchanged command permissions. Report sanitized diagnostics and portal status only.

The portal protocol is not a documented stable consumer API. Actual V3 portal login/ZIP retrieval, all Data Act mappings, right-door metadata, service/timer/charging semantics, GraphQL identity, physical controls and cross-model acceptance remain open. The original 91-field Q8 dataset proved schema and delayed capture, not V3 live authentication. Issue #44 and the audit in docs/V3_FEATURE_CLOSURE.md remain open for complete product acceptance. Stable V3 remains NO GO.

B31 product source is offered in upstream PR #918. This B32 package does not alter upstream review or upstream release metadata.
