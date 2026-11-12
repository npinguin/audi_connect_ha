# Audi Connect 3.0.0b16 — Q8 Completeness & Capability Discovery

**Experimental HACS test only.** V2 remains default and rollback choice. No normal completeness-qualified, stable or upstream release claim.

## Q8 live baseline

b15: 124 registered; 89 projected known (including unpressed buttons), 1 unknown, 7 unavailable, 15 not offered, 12 disabled. All 28 reviewed read routes assessed; 12/23 untruncated job schemas; 32/101 stored canonical scalar attributes normalized. 391 archived trips. Door and window details complete at the sample capture. Manufacturer metadata null, six charging state entities stale. No physical control acceptance. See [Q8 b15 diagnostics audit](V3_Q8_B15_AUDIT.md).

## Changes

- Keep original b13 inventory query; bounded automatic recovery via full V2-shaped and modern-header query on same Audi host. Preserve real manufacturer label provenance. Existing selected-VIN HA Device Registry model can be displayed only as last-known, not treated as manufacturer observation, model family, or control authorization. No new token destination or invented model.
- Four reviewed GraphQL read-only tests: original inventory, extended inventory, modern headers and render image query. No arbitrary GraphQL document or mutation; existing request budget and explicit manual action. Optional test evidence does not activate controls.
- Capture safe GraphQL error codes and known field paths, per selected vehicle only; no raw messages, other cars, image URLs or tokens in shared evidence. Latest identity sample and historical schema are distinct.
- Dashboard retains four tabs. GraphQL is applicable and independently testable; Vehicle Identity is visible in Capabilities; scan buttons support GraphQL; API evidence links fields to capability and target entity, with actual selected-car entity IDs in admin view where present. Shared diagnostics remain redacted. Search by capabilities, attributes and operations. Existing CARIAD/MBB workflows retained.
- Health distinguishes missing identity from no error and includes partial errors from shared status batch. No freshness thresholds relaxed or remote commands automatically executed.
- Review b15 projected and missing entities, structured details, field inventories, trip history and remaining data/semantic gaps. No unsupported feature is fabricated.

## Live acceptance

Install through HACS, restart the existing entry, keep V3 runtime and Workbench enabled. Inspect model/year/OEM drivetrain and presentation source; in the Workbench select GraphQL, Capabilities or API evidence, then test each variant individually or perform the full read-only scan. Export fresh diagnostics. Compare current charging, access, climate, maintenance, trips and position with actual vehicle/app; command testing must be explicit and safe. Missing API data, general-purpose visual mapping wizard, arbitrary route authoring, complete field disposition and physical validation remain open. Roll back to V2 if needed.

Full CI, Workbench UI, Hassfest, HACS and packaging must pass before publication. See [machine gate](../governance/V3_COMPLETENESS_GATE.json), [b16 authorization](../governance/B16_EXPERIMENTAL_TEST_RELEASE.json).
