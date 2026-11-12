# Q8 reference integration — b15 diagnostics, b16 disposition

Snapshot: HA 2026.11.1, Audi Connect 3.0.0b15, 2026-11-12. No VIN or personal values retained. This is a measured target-vehicle baseline, not a completeness or physical acceptance claim.

| Measure | b15 |
|---|---:|
| Registered HA entities | 124 |
| Projected (known, including unpressed buttons) | 89 |
| Projected unknown | 1 |
| Projected unavailable | 7 |
| Registered not offered | 15 |
| Disabled | 12 |
| Read assessment (23 selective jobs + 5 reviewed standalone routes) | 28/28 |
| Untruncated current-session job schemas | 12/23 |
| Canonical scalar catalog attributes normalized | 32/101 |
| Normalized historical trips | 391 |
| Physical controls verified in current context | 0 |

## Observed schema disposition and release scope

| Source | Evidence / disposition | Next live acceptance |
|---|---|---|
| Inventory | core/media/classification null; restore via reviewed full V2-shaped and alternate app-header queries, bounded; previous HA model presentation-only; capture safe errors; never infer identity from VIN | Confirm OEM model/year/drive and image; compare all variants |
| Access | door/window component arrays and overall/lock status; existing component summaries; capture 16.6 min, both complete | Check actual door/window/lock changes against HA |
| Charging | SOC/range, state/mode, plug, external power and LED captured; six state entities stale, one switch unknown | Real charge and unplug; verify values and timestamps; no stale state promoted to current |
| Charging timers | ID/enabled/climate/target/departure/preferred time windows mapped as structured details | Verify configured timers and preferred windows in actual vehicle |
| Climate | settings, state, invalid negative duration and sentinel window heating; existing guard preserved | Start/stop physically, check actual target and duration |
| Climate timers | ID/enabled/start/target local timestamps captured; structured detail; next timer may be absent | Configure timer; distinguish schedule from current state |
| Fuel / measurements | engine types, SOC/fuel/ranges and odometer; existing role-based selection | Cross-check all units/values with vehicle/app |
| Oil | boolean, not numeric volume | Confirm warning semantics; no invented numeric oil level |
| User capabilities | ID/expiry/status codes/user disabling; structured connected services | Verify meaning of status codes before treating as support |
| Inspection | mileage, oil service and inspection days/km | Cross-check vehicle maintenance data |
| Health warnings | empty warning envelope | Unknown, not all-clear |
| Lights | component names and states | Compare actual lamps |
| Position | captured timestamp; private coordinates withheld | Verify parked vs moving |
| Trips short/long/last | 391 records; mileage, travel time, consumption, speed, timestamps; shortTerm schema truncated | Validate sample values, units, archive coverage and restart |
| Remaining jobs | not-observed does not imply unsupported; chargingProfiles/readiness previously retryable 4112; tripStatistics HTTP 207 no usable schema | New live evidence under applicable operating conditions |

The 15 registered-not-offered entities: remaining charging time, charging completion time, remaining climatisation time, charge-mode select, preheater switch, next climatisation timer, current limit A/mode, plug auto-unlock, reported online/active, short/long reset, numeric oil level, target SOC number. These are not assumed supported. Keep the existing HA IDs, prevent fabricated values, and decide from new evidence. Full field-level semantic acceptance remains pending.

## b16 changes

Fixed reviewed GraphQL inventory variants and manual read tests on the existing tabs. API operations link to declared field/attribute/capability/product entity contracts; the admin dashboard resolves actual selected-car entity IDs where present. Historical/current field evidence remains separate. Identity error is visible in health. No automatic mutations, no unsupported-vehicle extrapolation, no new external token destination. General-purpose arbitrary read route authoring and full visual mapping builder remain out of scope for this candidate.

Normal completeness and upstream gates stay closed. Target validation requires a new b16 diagnostic snapshot, individual read tests and physical checks under safe conditions.
