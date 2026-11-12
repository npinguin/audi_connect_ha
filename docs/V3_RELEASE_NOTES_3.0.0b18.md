# Audi Connect 3.0.0b18 — Configure, Discover & Use

**Integrated experimental HACS test only.** All post-b17 changes are delivered in one package, not separate feature builds. V2 remains the default and rollback choice. Ordinary completeness, static parity, stable and upstream gates are unchanged. This release is intended for supervised real Home Assistant and vehicle acceptance.

## Changes since b17

- Product: automation-first Configure → Discover → Use, one native HA runtime and optional admin Workbench. Existing configuration and vehicle identities are retained. No additional integration or scheduler.
- Read discovery: shared per-vehicle completion/unresolved/pause status, bounded retries, quota-aware recovery, account-wide discovery budget rotation and explicit resume of unresolved reads through the existing coordinator. No automatic actuator or wake requests.
- Controls: reviewed compatible routes become eligible without physical discovery. Native guided Yes/No/Finish and Workbench guided/selective Expert mode share eligibility and durable command journal. Fresh changed comfort/charging readback can establish verification. One reviewed equivalent charging route may be tried only after definitive 405/410 plus explicit unsupported evidence; no repeat after timeout, acceptance or uncertainty. Edit failed APIs in the existing editor. Security-sensitive actions require explicit review.
- Identity: reviewed same-VIN manufacturer evidence can be explicitly adopted and refreshed on subsequent inventory polls; adoption preserves its own evidence. No arbitrary query activation, invented identity, blind token exchange or new host. The Q8 clean-install manufacturer model remains unproven.
- Engineering: shared field/value editor with JSON definition copy/paste, typed read/control parameters, immutable alternatives, bounded execution evidence and private reviews, native HA entity ↔ mapping ↔ API trace, and End-user validation view showing actual registered entities, discovery progress and timing. Full portable lifecycle and representative live acceptance remain open.
- Quality: full-catalog synthetic Configure → Discover → Use → Restart regression without Workbench; prior development baseline passed 1,049 Python tests, Workbench tests and validation. Exact release SHA must independently pass the complete pipeline before publication.

## Install and test (HACS)

1. Back up Home Assistant, including configuration, registry and private profiles. In HACS open Audi Connect from `npinguin/audi_connect_ha`, use Redownload / version selection and explicitly select `3.0.0b18` (show prereleases if needed). Restart HA.
2. Keep the existing integration/account entry. Select V3 in integration Options if not already active. Verify manufacturer model, model year, drive type, device identity, SoC, range, charging state and freshness against myAudi/vehicle.
3. Allow automatic read discovery to progress on its ordinary poll cadence. Check Discovery coverage and Integration status, unresolved jobs, retry and quota reasons. Resume only unresolved reads if needed.
4. Test the ordinary native HA entities and one deliberate supported control at the safely parked car. Check physical result, command/readback, timing and error messages. Do not repeat an uncertain command.
5. Optionally enable the Audi Engineering Dashboard. End-user validation shows the same progress, eligible actions and actual entity state. Guided or Expert tests require explicit action consent; inspect failed routes in Configure & Test. Compare the reviewed GraphQL and garage sources in Vehicle Identity and adopt only a matching real OEM result.
6. Restart/reload, verify preserved IDs and bindings, then test the V2 runtime rollback when appropriate. Do not delete registry entries. Package downgrade is distinct from runtime rollback; restore a compatible HA backup if necessary.
7. Share sanitized HA diagnostics and the actual observed results, not credentials or raw personal payloads. Use the [integrated A–Z acceptance matrix](V3_TEST_MATRIX.md).

## Known open acceptance

Seven ordinary HACS completeness gates remain pending validation: manufacturer identity, trip history completeness, structured details, health details, discovery, schema disposition and representative upstream matrix. Static parity, actual HA migration/rollback and physical vehicle acceptance are not certified. The test candidate does not grant stable or upstream promotion. See [completeness gate](../governance/V3_COMPLETENESS_GATE.json), [parity gate](V2_V3_PARITY_BASELINE.json) and [version-bound authorization](../governance/B18_EXPERIMENTAL_TEST_RELEASE.json).
