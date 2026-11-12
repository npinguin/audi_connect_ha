# Architecture closure — implementation progress

Current development work (2026-11-12) is not a release or parity sign-off.

Implemented:
- Account auth refresh lock, serialized transport and bounded quota recovery.
- Persistent normal command context before dispatch, restart uncertainty and cooldown, explicit review.
- Separate StatusEngine and CommandEngine composed by V3Engine; existing public HA service contracts retained.
- Generic non-climate status evidence and restore; dynamic HA projection on all nine platforms.
- Pure automatic fast control resolution with catalog-matched versus versioned local evidence, user-disable/impairment/security checks, no actuator calls during discovery; one persisted evidence snapshot per poll.
- Machine-readable current module ownership; synthetic regression tests.
- Removed obsolete V3Runtime, inherited coordinator and first climate implementation/catalog from production. Minimal catalog remains test-only; persisted runtime selector stays unchanged.

Still open:
- Fully generic catalog/attribute schema, status planning and custom parameterized operation activation/PUT; current historical job mapping remains.
- Complete command journal (all attempts, durable request ID, physical readback) and shared lifecycle for engineering and normal commands, including specialized security preflight; current normal context is last-command only.
- Reconcile removed vehicles/context changes and full HA integration acceptance.
- V2 upstream delta register, CI dependency/type/coverage gates, generated parity and actual vehicle/recorder/rollback proof.
- Review actual catalog eligibility across supported vehicle families. Catalog match is not physical proof.

Do not mark static parity or release gates complete.
