# Audi Connect 3.0.0b11 — maintainability, freshness & response coverage

Experimental HACS test only, subject to exact-SHA CI. Includes b10 product rationalisation and Engineering Dashboard.

- Shared product/category policy for native entities and registry migration.
- Behavioral regression coverage for projection, valid zero, invalid boolean, deduplication, control eligibility, user choices and rollback.
- Shared capture-age policy; conservative freshness across observed API jobs, with job coverage in diagnostics and status reports. Historical age retains newest-capture meaning.
- Explicit bounded response field truncation and timestamp metadata classification. Existing observation records with or without field inventory remain valid; orphan truncation metadata is rejected.
- No additional Audi API requests, new physical commands or V2 business logic changes.

## Acceptance
Back up HA and install b11 once published. Verify b10 entity categories and compatibility visibility, Q8 climate/charging availability, Engineering Dashboard navigation, job freshness and response field coverage. Export new diagnostics. Preserve existing IDs and V2 runtime fallback.

Open: mirrored custom automotive icons, full vehicle identity, historical registry cleanup, complete per-job mapping coverage and physical Q8/ICE/BEV acceptance. No stable or static parity claim. A backup is needed for package downgrade if newer profile fields are saved.
