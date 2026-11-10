# Audi Connect 2.5.3b13 — restore probe usability fix

This isolated HACS prerelease builds on 2.5.3b12 and is intended for explicit, read-only Audi Q8 PHEV discovery. **No new sensors are switched on, no Audi remote actions are changed, and the fork's main branch remains at b11.**

## Why b12 showed Unknown error

The previous Core probe at 22:49 CET on 10 November 2026 and the Restore attempt at 22:55 CET were within the built-in 15-minute per-vehicle cooldown. b12 raised a plain RuntimeError. Home Assistant displayed **Unknown error** instead of an actionable message. b13 preserves the same cooldown but forwards a readable message with the remaining minutes.

## Unknown API call budget

Audi may omit the `Vcf-Remaining-Calls` response header. b12 therefore discarded the entire Restore test without a single GET.

In b13:
- With a **known budget of at least 20**, up to eight fixed, read-only restore GETs may execute, reserving at least 12 reported calls.
- With **no known budget**, the probe is strictly limited to **five** GETs: short-term, long-term, last trip and two alternative tripstatistics routes. 12V, TPMS and vehicle-health probes are marked `skipped` with `unknown_budget_probe_cap_reached`.
- With a **known insufficient budget**, no probe calls execute.
- HTTP 401/429, server failures, timeout and unexpected transport errors stop the sequence immediately.
- The 15-minute cooldown prevents repeated probing. Only explicitly user-initiated service calls reach the new endpoints. No background poll or automatic retry is introduced.

## Test

1. Back up Home Assistant. Install **2.5.3b13** from the GitHub/HACS prereleases and restart Home Assistant. Keep the existing Audi Connect config entry.
2. Go to Developer Tools → Actions, select **Probe known read-only Audi API paths**, choose the Audi vehicle and set **Restore** on, **Extended** off.
3. If a previous probe ran within 15 minutes, the action should show a cooldown message instead of `Unknown error`. Do not bypass the cooldown.
4. When eligible, perform the action **once** and immediately Download Diagnostics from the Audi Connect integration.
5. Share only the sanitized `read_only_api_probes` section, without raw VINs, accounts or authentication tokens.
6. Confirm that lock/unlock, flash lights, stateful climate switch, telemetry and existing entities remain unchanged.

Expected with unknown budget: `mode=restore`, `attempted <= 5`, the first five trip probes attempted or stopped earlier by an API error, and 12V/TPMS/warnings skipped. HTTP 200 means the route was readable, not that the response was a valid trip dataset.

Feature restoration remains research-only until actual Audi response schema evidence supports a correct provider and parser.
