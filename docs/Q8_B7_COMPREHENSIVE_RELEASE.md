# Audi Connect v2.5.3b7 — Comprehensive Q8 beta (functional fixes + features)

## What is actually proven
Owner's Audi Q8 PHEV on prior v2.5.3b5:
- **Physical success**: climate start, climate stop, door unlock, flash lights.
- **Physical failure**: door LOCK; CARIAD returned HTTP 200 but vehicle did not lock.
- Car data, parking position and 72 capabilities were readable.
- Climate timers and vehicleHealthInspection were independently confirmed to
  return readable JSON by the owner's explicit 13-GET diagnostic probe.
- HTTP 429 was observed after multiple access calls; avoid automatic retries.

This release is a **single integrated functional iteration**. Automated tests and
hassfest are required before publication. No real Q8 commands are executed by CI.
Do not describe lock as fixed without physical confirmation.

## Delivered improvements

### Access and command reliability
- Preserve working b5 CARIAD access/lock/unlock, climate start/stop and flash APIs.
- Lock entity already refuses to report success from gateway HTTP 200 alone
  when the refreshed car state has not confirmed locked.
- The platform now suppresses the connection's extra notify/refresh and performs
  one explicit post-command refresh. Direct service callers retain the prior
  connection-level notification by default. This reduces needless calls and
  rate-limit pressure without modifying the physical command payload.
- Lock vs unlock HTTP outcomes have distinct, redacted diagnostic route
  identifiers. Sensitive VIN/S-PIN/request IDs are excluded from the
  confirmation warnings and rejection messages.
- No lock retry, access fallback, or automatic PIN verification is attempted
  without actual evidence; none are safe guesses after an HTTP 429.

### Capability-driven CARIAD reads
- The first selectivestatus poll requests the fixed legacy set, preserving
  discovery on vehicles without userCapabilities.
- When the vehicle supplies a valid capability list, subsequent calls request
  only explicitly advertised, healthy jobs plus userCapabilities itself.
  The plan is per-VIN, kept only for the live session, and changes when a new
  capability snapshot arrives. Unknown list => original full query.
- Missing chargingProfiles or auxiliaryHeating jobs no longer generate
  avoidable errors when Audi explicitly reports that the Q8 lacks them.
- **No additional network requests** are made by capability planning.

### Real climate timer entities
- Parse the confirmed CARIAD climatisationTimersStatus.value.timers as an
  allowlisted, bounded list (up to 12 timers, no location/raw fields).
- Show **Climate Timers Enabled** and **Next Climate Timer (Car Local Time)**
  as ordinary HA sensors on the original Audi device.
- Keep the vehicle's startDateTimeLocal as a local-clock string. Never claim a
  timezone-aware HA instant or infer the vehicle's timezone without evidence.
- Timers are read-only. A configured timer is not a guarantee that climate
  actually starts and no new remote timer-setting command is enabled.

### Data resilience and earlier b6 fixes
- A partial HTTP 200 with per-job errors merges valid new fields instead of
  wiping values from other jobs. An all-error response keeps previous data.
- A sparse/untimestamped status response keeps the previous real vehicle update
  time rather than replacing it with the 1970 sentinel. This does **not** mark
  preserved values as freshly measured.
- b6 Model fallback, Park Time source indication, native GPS tracker
  freshness, and existing unique IDs are retained.
- Protect RHI Mobility from spurious source entity disappearance.

## HA practical acceptance gate

1. Back up Home Assistant; install the HACS beta ZIP under the same integration,
   retain config entry/device/entity registry and restart.
2. Verify Model, Park Time and GPS Position source/freshness against myAudi.
3. Verify the new Climate Timers Enabled sensor appears if
   climatisationTimers is reported. Check the number and local time against app.
4. Physically check **Unlock**, **Start climate**, **Stop climate**, **Flash**.
5. Do **one** LOCK test beside the stationary car with all doors and tailgate
   shut and the key outside. Observe actual doors + myAudi action history.
   HTTP 200 is not physical success. If unconfirmed, capture redacted diagnostics
   and do not loop commands during the known rate-limit window.
6. Observe the latest cloud poll timestamp and car data freshness separately.
   A successful poll with stale parked vehicle readings is not a cloud outage.
7. Confirm no duplicated source device, entity IDs or new Audi logins.
8. Compare the car's reported capabilities to the effective job selection.

## Remaining known blockers
- Real physical LOCK not proven. Need paired, rate-limit-safe evidence:
  one POST access/lock status + next actual car doorLockStatus/capture timestamp,
  optionally myAudi command history. Never publish user PIN, VIN or HAR.
- CARIAD may enforce per-vehicle, region, equipment or door-safety preconditions.
- Charging settings still have a Q8 job-level error; don't guess payloads.
- Separate Trips GET and vehiclewakeuptrigger are candidate routes, not enabled
  automatically in this beta.
- Repository default branch/master and GitHub Issues setting may block complete
  HACS validation until admin changes them.
