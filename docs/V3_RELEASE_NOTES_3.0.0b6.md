# Audi Connect 3.0.0b6 — V3 Automatic Discovery & Guided Controls

**Experimental test release — not feature complete.** This version addresses
the November 11 b5 observation that the Workbench listed many V2 references
as "not tested" while the Q8 returned only a few climate mapping attempts.

## What's new

- On first CARIAD startup, perform one bounded 23-job read-only
  selectivestatus batch and up to two smaller safe targeted GET probes if
  known V2 mappings are missing. Unobserved fields are not marked unsupported;
  further probes are spaced out and each job is tried at most once automatically.
- Persist vehicle-scoped job discovery: observed, not observed, inconclusive,
  and jobs still awaiting scan. No VIN/token/raw private response is exported
  in diagnostics.
- Show a simpler 3-step Workbench: results first, grouped capability cards,
  and a vehicle-specific CARIAD/MBB API-family filter. Technical route evidence
  and raw historical references are collapsed. Text uses Home Assistant
  typography variables instead of tiny fixed-size fonts.
- Add independently testable CARIAD remote-control variants from historical V2:
  wake-up, charging start/stop (including separate *manual* combined-route
  alternatives), window heating start/stop, access lock/unlock, and existing
  climate start/stop. These are candidates, not automatically enabled controls.
- After physical review verifies a route for this car, create matching
  Home Assistant buttons, the climate ON/OFF switch, or door-lock entity
  using their historical V2 unique IDs. Re-enable only those verified entities
  in the reversible V2/V3 registry migration.
- Door access requires the account's configured S-PIN, and refuses to claim
  a lock state without a valid fresh reading. PIN values are not stored in
  local route profiles or displayed in preview/diagnostics.
- Keep separate CARIAD, MBB-legacy and GraphQL executors; MBB control
  migration and several derived V2 fields are *not* complete.

## How to test safely

1. Back up Home Assistant. You can reselect V2 — Stable in the existing Audi
   config entry at any point. Do not create a duplicate integration.
2. Install the `3.0.0b6` prerelease from GitHub/HACS or the provided ZIP,
   restart HA and enable V3 — Experimental + Development Workbench.
3. In **Step 1**, select your vehicle and use **This vehicle · CARIAD**.
   Check readable attributes, the number of observed status jobs and data
   freshness. The full historical backlog is available in the collapsed section.
4. In **Step 2**, choose Charging, Climate, Access or Remote. Select
   a specific read-only attribute or one of the now-visible control actions.
5. In **Step 3**, run GET tests safely. To test a POST action, be with the
   car, select a route, press **Send one test command**, observe what the
   vehicle physically did, and review as Worked, Failed or Not sure.
   **Never repeatedly try another route on uncertain results.**
6. When a control has been physically verified, check that the matching native
   HA button/switch/lock entity appears, stays enabled, and retains its
   original unique ID. Some entities require valid fresh car status.
7. Record missing attributes, GET mapping statuses, control-route outcomes and
   HA entity differences. Don't share a VIN, S-PIN, tokens, coordinates or
   raw private cloud payloads.

## Still open

- Complete historical V2 feature and entity-type parity, especially derived
  status and service data, legacy MBB controls, timers and custom settings.
- Real-vehicle verification of every CARIAD control route. An HTTP 2xx/202
  response is not physical confirmation.
- Robust multi-vehicle discovery, regional routing, rate-limit recovery,
  and live V2↔V3 rollback validation across restarts.

The release workflow runs the complete test suite, Node Workbench tests,
HACS, Hassfest, packaging and publishes only the verified immutable SHA.
