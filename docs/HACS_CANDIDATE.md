# Audi Connect 3.0.0b41 — owner field-test candidate

Experimental HACS prerelease for initial local testing. V2 remains the default and rollback; V3 is opt-in. No stable promotion or general field-test announcement yet.

## What changed

- Retain selected last-known native vehicle readings during sleep and restart; restored data is historical, not a fresh vehicle observation.
- Controls use a shared, explicitly marked optimistic state for up to five minutes. Newer vehicle observations and rejected or superseding commands take precedence. Restart never restores optimistic intent.
- Retain existing entity identities and command history. Delayed responses no longer silently overwrite newer captures.
- Shared guided discovery for climate, charging and other supported controls, including temperature parameters and selective retest. Open Vehicle Setup & Discovery after upgrading.
- Consolidated ownership of status, command evidence and HA projection. No extra API calls or automatic wake/retry.

## Local acceptance

1. Back up Home Assistant, update to B41 and restart without deleting the integration or devices.
2. Run Vehicle Setup & Discovery from the V3 integration options. Test the discovered climate, locking and charging controls.
3. Verify physical charging START and STOP against actual power, not only the switch. The reported physical STOP issue remains open.
4. Verify sleeping and restarted vehicle states, preserved entity IDs and history, and charge mode selection.
5. Verify EU Data Act separately after native controls; enable it only if authorized. Existing connections may be kept.
6. Export diagnostics after testing. Do not include credentials or raw private vehicle data in public reports.

Source: merged PR #57, e856caa1f8c4dd698a6f758716d7bc4975da80bb. Exact product head eb451a1 passed 1,297 Python tests, 43 Workbench tests, lint, formatting, HACS and hassfest. The candidate workflow independently checks both supported HA targets and packaging. Physical Q8/Q5 acceptance and stable gate #44 remain open. No claim that OEM STOP is fixed.
