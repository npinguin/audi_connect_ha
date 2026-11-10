# Audi Connect v2.5.3b8 — Q8 feature parity + native controls

## One bundled release, no diagnostic-only mini iterations

This extends v2.5.3b7 and consolidates the standalone
[CarConnectivity Audi connector](https://github.com/acfischer42/CarConnectivity-connector-audi)
feature review into one native Home Assistant Audi integration.
The reference project is MIT-licensed (Achim Fischer, 2025).
We adapt the API concepts; we do not embed CarConnectivity's extra runtime,
MQTT bridge or its legacy credential/session stack.

**Real Q8 b7 field results (owner, 10 Nov 2026):**
- LOCK and UNLOCK both physically WORK.
- Climate ON and OFF both physically WORK.
- Flash lights physically WORK.
- Most recent native diagnostics: HA 2026.11.1, Audi Connect 2.5.3b7,
  healthy Auth0, 64 entities, per-vehicle rate-limit reading 47.
- Reported capabilities include charging, climatization, dealerAppointment,
  onlineCarCare, vehicleWakeUp and vehicleWakeUpTrigger.
- Modern dealer metadata was not returned, model enrichment still unavailable.
- B8 code is unit-tested, **not yet physically accepted on the owner's Q8**.
  Do not mistake unit tests for live vehicle proof.

## New / improved Home Assistant features

1. **One-tap climate ON/OFF**: new native `switch.*climate_quick_control`
   ('Climatisation ON/OFF'). One reversible entity replaces two buttons
   on the dashboard, reusing the *exact* physically proven CARIAD bodyless
   climate start and climate stop. Audi status is source of truth; no
   optimistic 'success', no duplicate refresh. The existing climate entity,
   start/stop buttons and all unique IDs remain intact.
2. **Door Lock/Unlock UX**: already a native `lock` entity with both actions
   and physical state. Dashboard tile with optional `lock-commands` feature,
   or use HA's single native Lock/Unlock control in its detail dialog.
   Do not create a misleading `switch` for a security-sensitive action.
3. **Dealer**: native Audi Configure flow, optional per-VIN dealership,
   telephone, address, website, upcoming appointment and warranty expiry.
   'Dealer (local)' is visible before configuration with 'Not configured'
   state; 'Service overview' combines car inspection/oil information with
   separately marked local appointment/warranty data. No claim that a
   dealer name was fetched from Audi cloud.
4. **More status fields from CARIAD**: vehicle-reported online and active,
   AC charging current (A), current-limit mode, and auto-unlock charging plug.
   Read-only, capability- and source-driven; unknown is not false.
5. **Safer SOC settings**: Auth0 reads the car's current charging settings,
   preserves relevant preferences, and changes only requested target SOC.
   Refuse blind PUT if settings are unavailable. Actual write authorization
   on this Q8 is not yet physically confirmed.
6. **Experimental commands (default OFF)**: explicit Configure opt-in and
   car-reported capability required for charging start/stop, window heating
   start/stop and manual vehicle wake-up. No automatic wake, no arbitrary
   fallback, no blind retries.
7. Existing b7 climate timers, per-capability polling, Model fallback,
   Park Time estimates, GPS source/age, partial-poll resilience, and
   lock/unlock/climate regression checks are retained.

## Deployment

- Full HA backup; update via HACS pre-release `v2.5.3b8`, restart HA.
- Confirm the Audi Q8 device has 'Climatisation ON/OFF' under Switch,
  an existing 'Door lock' under Lock, and the previous Climate entity.
- In **Settings -> Devices & services -> Audi Connect -> Configure**,
  choose 'Edit dealer and local service details' to open a per-car form.
- Add a HA tile with `type: toggle` for the new climate switch and a lock
  tile with `type: lock-commands` for doors. Example in
  `docs/Q8_NATIVE_CONTROLS_UX.md` (entity IDs are placeholders).
- Do one physical regression check each for ON/OFF and LOCK/UNLOCK,
  compare HA state against myAudi/vehicle, and verify no entity ID changes.
- Only enable 'experimental_commands' when you intentionally want to
  test a model-supported remote feature. These are not accepted as working.
- Check dealer/service fields and read-only status fields; their presence
  depends on Audi returning the corresponding capability/values.
- Confirm HA availability (last cloud poll) and actual car data freshness
  remain distinguishable.

## Volkswagen ID.4

HA dashboard patterns can be shared, but the Audi backend cannot be pointed
at a Volkswagen account. VW uses different authorization/service policy.
As of 2026-11, VW Group Connect documents European ID.4 (MEB) as
read-only following the modern two-way auth restrictions. The user's
preinstalled `vag_connect` integration may be used for read-only
telemetry; RHI Mobility should consume each brand through native HA source
entities. Do NOT invent working VW ID.4 lock/climate endpoints from Audi Q8
success. Reference:
https://github.com/its-me-prash/vwgroup-connect-ha

## Release quality gate

- Python pytest PASS, Home Assistant hassfest PASS for exact release head.
- HACS metadata validation may separately fail because GitHub Issues are
  disabled in the fork's repository settings; do not call it green.
- No real PIN, VIN, OAuth, precise location or raw response in any test fixture.
- An HTTP 200 is never evidence of a physical command until field testing.
- Upstream: separate minimal patches only after b8 live acceptance.
