# Audi Connect 3.0.0b19 — Product closure and community diagnostics

**Development candidate; not yet authorized for publication.** This is one integrated candidate above b18. The existing published b18 remains available for HACS testing. V2 remains the default and rollback choice. Normal completeness, parity, stable and upstream gates are not waived.

## Changes

- Preserve post-b18 identity and Workbench improvements. Manufacturer metadata remains an OEM/auth-context investigation; do not invent an identity or new credentials.
- One persisted command journal owns the wake/refresh cadence across restart and journal eviction. Unconfirmed security-sensitive acceptance requires review; no automatic replay.
- Known request allowance is conservatively debited before dispatch; missing headers cannot silently make the budget unlimited.
- Both directions are required for a native operational switch. An individually eligible action can retain its independent button. Charging-write failures on the reference Q8 are not a V3 regression or a global capability exclusion.
- Discovery and diagnostics share context-scoped physical outcomes. An inconclusive job is not silently downgraded by an empty follow-up; positive evidence resolves it.
- Community diagnostics schema 2 includes canonical attribute statuses and structural API evidence, strips all response previews and duplicate schema fields, and documents historical-only deltas and quota provenance.
- No-op profile saves are skipped. No additional runtime component or parallel store.
- The release pipeline derives the version from the manifest, tests the supported HA floor and the reference installation version, and retains immutable exact-SHA packaging and explicit release authorization.

## Acceptance still required

Full static V2 parity and upstream reconciliation, live manufacturer identity and schema/attribute disposition, representative vehicle and browser acceptance, reload/restart and V2 rollback remain open. Existing governance gates are unchanged. A passing CI run alone is not a release authorization.

Reference b18 owner evidence: 125 registered entities, 95 projected known including buttons, 392 normalized trips, six stored locally verified controls. Charging writes did not work in either V2 or V3 on the current Q8 configuration. Do not force them or label them globally unsupported. See [community diagnostics](V3_COMMUNITY_DIAGNOSTICS.md) and the [completeness gate](../governance/V3_COMPLETENESS_GATE.json).
