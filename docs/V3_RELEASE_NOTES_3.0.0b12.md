# Audi Connect 3.0.0b12 — native climate, discovery & product naming

Experimental HACS test only. Publication requires exact-SHA validation. V2 remains the default and rollback runtime; no static parity, physical acceptance or stable promotion is claimed.

## Changes

- One primary native Climate entity with separate semantic on/off and target temperature, backed by eligible OEM routes. Explicit start/stop buttons retired by identity; compatibility switch remains opt-in.
- Requested, staged and reported climate temperature are distinct; readback and command acceptance are not conflated.
- Engineering Dashboard shows masked request and response evidence and bounded historical executions without extra API calls. Full read-only catalog scan is resumable and quota-aware; no automatic mutations.
- Cross-domain capability evidence in diagnostics, canonical capability ownership and three modern trip routes included in mobility discovery. Regular trip and parking polling contributes engineering evidence.
- Functional product names for all 112 built-in identities; no API family or development labels in integration-owned names. Registry original labels are migrated even for unavailable records, preserving user labels, IDs, automations and history.
- Parity inventory synchronized with actual catalog additions; full release gate unchanged.

## Acceptance

Back up HA, select b12 in HACS and restart. Confirm native climate on/off and setpoint, actual readback, clean entity names, registry identity and retained automations. Check request and response inspection, full read-only discovery and updated diagnostics. Hidden aliases may appear in HA administrative views with HA's own Hidden marker.

Open: charging and window heating native switches pending status evidence, model identity, timer and health mapping, remaining legacy routes, physical Q8/ICE/BEV acceptance and rollback validation. No claim of stable readiness.

## Release candidate correction

The first unpublished candidate passed 849 tests but failed three release metadata checks: stale manifest blob in the V2 delta register and two b11-specific test expectations. The corrected candidate derives test expectations from the active manifest and validates the matching authorization, notes, package and exact-parent guard. No test gate is bypassed and no existing tag is replaced.
