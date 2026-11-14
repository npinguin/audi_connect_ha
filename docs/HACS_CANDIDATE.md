# Audi Connect 3.0.0b42 — owner self-test candidate

Experimental HACS prerelease. V2 remains the default and rollback; V3 is opt-in. This is a targeted correction to B41, not a stable promotion or general field-test announcement.

## What changed

- Previously verified controls no longer become permanently blocked by old routine command outcomes, including B41 legacy lock/unlock records without per-command HTTP status.
- Keep discovery bindings and historical outcomes separate. A failed or uncertain routine command does not revoke a proven binding. A new explicit request may be made after the existing bounded cooldown.
- Restore accepted historical outcomes without inventing HTTP evidence or replaying commands. Interrupted, unacknowledged operations remain uncertain.
- Preserve authorization, route applicability/revision, parameter validation, active discovery review and wake quota/cadence guards.
- B41 state continuity, entity identities, canonical last-known status and bounded optimistic projection remain intact. No new polling, automatic retries or state layer.

## Local acceptance

1. Update via HACS and restart without deleting the integration or existing history.
2. Before running discovery, verify that previously proven lock and unlock are both usable. Inspect actual vehicle response and export diagnostics.
3. Run Vehicle Setup & Discovery for unresolved controls; test climate, charging and charge mode.
4. Confirm that sleep, restart and temporary command failure do not erase previously proven bindings. Verify physical charging against measured power.
5. Keep EU Data Act separate from native command validation; check it after native controls.

Source: merged PR #58, 8d1dbbb677c0c2ba3290c995718703b89ffd03f5. Exact reviewed head 1cb911f1cdc3c5d94858f86313994e8fed6912ac passed 1,298 Python tests, 43 Workbench tests, lint/format, HACS and hassfest. The candidate workflow independently checks both supported HA targets and packages the release. Physical Q8/Q5 acceptance, charging START/STOP behavior and stable gate #44 remain open.
