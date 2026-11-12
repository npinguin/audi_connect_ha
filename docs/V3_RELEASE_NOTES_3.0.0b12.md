# Audi Connect 3.0.0b12 — native climate, discovery & product naming

Experimental HACS test only. Publication requires exact-SHA validation. V2 remains the default and rollback runtime; no static parity, physical acceptance or stable promotion is claimed.

## Community value — more than a new release

V3 introduces a capability-driven evolution of Audi Connect: more vehicle information, native Home Assistant controls, reliable interpretation of data and a way for the community to discover and contribute missing functions. Ordinary users can use eligible known capabilities without configuring API routes; explorers can investigate gaps; engineers can discover, configure, test and locally activate verified routes where supported, then share reusable evidence.

- **Users:** connect myAudi, select V3 and use the native vehicle entities.
- **Explorers:** enable the optional Engineering Dashboard and investigate read-only capabilities, data and mapping gaps.
- **Engineers:** discover alternative paths, configure local attributes or command candidates, validate the result, activate eligible verified routes, and contribute the evidence for reviewed shared catalog rules.

See the [community quick start and engineering how-to](V3_COMMUNITY_HOWTO.md) for exact UI steps and a contribution template, and the [proposed upstream README section](V3_UPSTREAM_README.md) for community-facing release messaging.

This section describes b12 and its intended contribution model; it does not claim new post-b12 functionality, automated contribution export/import, full parity or stable readiness. This is a documentation supplement on the development branch; the published b12 tag remains unchanged.

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
