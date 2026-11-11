# Audi Connect 3.0.0b3 — V3 Stable Discovery Baseline

**Experimental HACS prerelease** — back up Home Assistant before installing.
This is a stabilization of 3.0.0b2 on the **same V3 branch and PR #20**.

### Fixed
- **Save candidate** persists a developer-selected API path per vehicle and
  aspect without incorrectly marking it as tested or enabling a control.
- **Activate verified path** remains separate and requires a genuinely
  valid, fresh GET result or confirmed physical climate action.
- The HA Options flow handles runtime changes without dropping historical
  V2 configuration, including dealer metadata and experimental flags.
- V3 Development Workbench is **off by default**, visible in the sidebar
  only after enabling it while V3 is active; it is removed when switching
  to V2, with all private V3 profiles retained.
- A cloud HTTP response alone no longer makes hours-old Climate data fresh.
  A capture timestamp must be recent; stale vehicle state is distinguished
  from online cloud polling.
- The Workbench preserves route dropdown selections across rerenders.

### New capability overview
- **Capability Status Dashboard:** one view per vehicle showing the known
  climate attribute/control mappings, API family, template path, evidence,
  state and active/draft route selections.
- Historical read-only selective-status jobs and known routes from V2 are
  shown as **V2 reference / not migrated**, not as verified or discovered.
  This is a concrete migration inventory for the next engineer to test.

### Still experimental
The live Audi Q8 must confirm the Options toggle, V3 startup, status
capture timestamps, Workbench save/reload, and V2 rollback. Green CI does
not verify an actual climate control action. The model still migrates
**Climate only**; charging, trips, battery, locks, health and other historic
features remain in V2 until independently discovered and migrated to V3.
Automatic sequential physical control tests remain disabled.

Read [Why / What / How](V3_ARCHITECTURE.md),
[configuration and rollback](V3_CONFIGURATION.md),
[capability model](V3_DEVELOPMENT_PROFILES.md), and
[test matrix](V3_TEST_MATRIX.md).
