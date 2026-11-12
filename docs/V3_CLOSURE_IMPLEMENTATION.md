# Architecture closure — implementation progress

Current development work (2026-11-12) is not a release or parity sign-off.

Implemented:
- Account auth refresh lock, serialized transport and bounded quota recovery.
- Persistent normal command context before dispatch, restart uncertainty and cooldown, explicit review.
- Separate StatusEngine and CommandEngine composed by V3Engine; existing public HA service contracts retained.
- Generic non-climate status evidence, scheduling, mapping of scalar capability observations and restore; dynamic HA projection on all nine platforms.
- Serialized profile writes, durable CARIAD request IDs, post-command readback for known stateful actions, and journal persistence before special engine proof preparation.
- Pure automatic fast control resolution with catalog-matched versus versioned local evidence, user-disable/impairment/security checks, no actuator calls during discovery; one persisted evidence snapshot per poll.
- Machine-readable current module ownership; synthetic regression tests.
- Machine-readable V2 upstream delta inventory and a blob-integrity regression gate (review required, not semantic parity).
- Removed obsolete V3Runtime, inherited coordinator and first climate implementation/catalog from production. Minimal catalog remains test-only; persisted runtime selector stays unchanged.

Still open:
- Fully generic catalog/attribute schema and HA projection, custom parameterized operation activation/PUT; current historical attribute/job mapping remains.
- Complete bounded command journal history and single lifecycle representation for engineering and normal commands; current normal context is last-command only, readback covers known stateful actions and does not prove transient actions.
- Context-change migration and full HA integration acceptance. Inventory removal and return are implemented.
- Review all pinned V2 upstream deltas; CI dependency/type/coverage gates, generated parity and actual vehicle/recorder/rollback proof.
- Review actual catalog eligibility across supported vehicle families. Catalog match is not physical proof.

Do not mark static parity or release gates complete.

- Vehicle inventory reconciliation retains object/entity identity, blocks excluded or repeatedly missing VINs, and restores them on rediscovery. Empty/malformed responses do not revoke existing vehicles. Context-change migration remains a separate acceptance item.
