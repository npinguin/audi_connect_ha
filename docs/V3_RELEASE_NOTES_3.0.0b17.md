# Audi Connect 3.0.0b17 — Vehicle Identity Recovery & Charging Readiness

**Experimental HACS test only.** V2 remains default and rollback choice. Ordinary completeness and upstream gates remain closed.

## Evidence and hypothesis

b13 returned non-null manufacturer model/year/drivetrain on the original GraphQL request. b14/b15 returned null metadata under Auth0, same configured region and query. External VW Group Connect Audi implementation documents a similar Auth0/AZS exchange restriction and an independent CARIAD garage inventory source. This is a hypothesis, not proof of the historical transition on the Q8. See https://github.com/its-me-prash/vwgroup-connect-ha/blob/main/custom_components/vag_connect/cariad/api/audi.py and https://github.com/its-me-prash/vwgroup-connect-ha/blob/main/custom_components/vag_connect/cariad/api/vw_eu.py.

## Changes

- Read-only CARIAD GET /vehicle/v1/vehicles on the existing regional BFF; explicit exact-path/method restriction. Selected VIN only, no inventory membership change, no nickname as manufacturer model. Match known GraphQL VIN, fill missing OEM model/year with independently sourced garage metadata; keep model and year source and private cache. Never infer drivetrain from allocation type.
- Initial GraphQL baseline then one bounded optional garage read and original query after garage, recorded under a distinct operation, followed by existing reviewed variants if metadata still missing. No automatic wake, mutation, arbitrary destination, token exchange or reauthentication. Existing quota/authorization rules retained. Failed optional reads do not block normal polling.
- Workbench Vehicle Identity links CARIAD and GraphQL sources to model entity; individual Test and API evidence, including post-garage comparison. Tests are evidence only, not route activation. Model recovery is automatic at inventory discovery.
- Safe request authentication evidence: provider, token slot, same-as-CARIAD, coarse audience, known scopes, age; unverified claim parsing is diagnostic-only. No raw JWT/subject/client secret. Recognize known token exchange denial text as a fixed reason, never retain raw errors.
- Charging ready binary sensor differentiates explicit readyForCharging and notReadyForCharging, independent of charging active; unknown for other values and unavailable on stale data. Existing charging switch guards unchanged.
- Target validation remains open: OEM identity may still be missing in both API families; no live proof of source order or token exchange cause. Image recovery remains dependent on authorized OEM response. No further arbitrary host or credential exchange implemented.

## Test

Update via HACS to b17 and restart. On Vehicle Identity in Workbench (all API families), inspect original GraphQL, CARIAD garage, post-garage GraphQL, extended/modern and images. Test each independently; the post-garage test performs garage then original query. Compare HTTP, non-null fields and authentication evidence. Export diagnostics. Verify model/year provenance and actual charging readiness with the car parked and safely connected/disconnected. Do not treat readiness as authorization or active charging. If garage source has no model, do not fabricate it. Physical acceptance and cross-model evidence remain pending.

Full CI, Workbench UI, Hassfest, HACS and packaging required. See [machine gate](../governance/V3_COMPLETENESS_GATE.json) and [b17 authorization](../governance/B17_EXPERIMENTAL_TEST_RELEASE.json).
