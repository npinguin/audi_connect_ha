# Audi Connect V3 — Climate Pilot (3.0.0b1 development candidate)

## Why V3

One Audi Connect config entry; one authenticated session; one cloud polling
coordinator; one climate capability with independently optional status and
control. Clean V3 registry/runtime is adjacent to the V2 code — no forked
authentication, no extra scheduled cloud GET, and no duplicate climate entity
with a new unique ID.

**Status:** Experimental pilot, only validated code gates and synthetic tests.
This commit is not proof of successful physical action on a real Q8 and is
not a published GitHub Release until an actual release/tag exists.

## Turning V3 on (after installing the candidate via HACS or manual custom integration)

Open **Settings → Devices & Services → Audi Connect → Configure/Options**.
Choose **Runtime generation: V3 Climate**, save, and let HA reload the same
config entry. No new Audi login, VIN selection or duplicate integration is
required. The same `climate.climatisation` unique ID is reused. To roll
back, select **V2** and save.

V3 currently applies the new climate entity only to **Auth0/CARIAD vehicles**.
Legacy vehicles deliberately remain on the proven V2 climate entity. Other
sensors, switches, controls and charging entities still use the existing V2
implementation and API adapter until their own capability migration.

## Climate behavior

- A single HA climate entity owns ON/OFF; the extra CARIAD quick switch is
  not created in V3. Old switch registry entries are not deleted. **Any
  automation using the old quick switch must be reviewed before enabling
  V3**, since HA may mark that entity unavailable until V2 is restored.
- V3 exposes ON/OFF, not a target-temperature slider on the Q8. The car's
  real reported state drives the mode; unavailable source data is not OFF.
- For trusted Audi Q8 models, default Auth0 start uses the existing **bodyless** CARIAD start with vehicle-stored settings; other Auth0 models default to the settings adapter. Users may explicitly select the existing
  **vehicle-settings** variant (it requires a valid reported vehicle target);
  this is never an automatic fallback.
- Stop uses the existing CARIAD stop adapter. Commands are not retried.
  A gateway acknowledgment is not proof the car acted; the entity displays
  a separate confirmation hint and does not fabricate physical state.
- Options `v3_climate_status_route` and `v3_climate_start_route` select
  only reviewed known API operations. Unknown arbitrary hosts and tokens
  are not accepted.

## Ownership and a clean migration seam

`v3/climate.json`: one brand catalog with optional per-operation scope
(filters for auth/region/vehicle type/model are supported by the resolver).
`v3/registry.py`: pure validation, choice and local evidence. No network.
`v3/runtime.py`: one config-entry runtime, per-vehicle route evidence,
sanitized capability diagnostics, explicit selection options.
`v3/coordinator.py`: inherits HA's existing coordinator and keeps **one**
scan interval, cloud refresh and refresh-action trigger. The V2 AudiAccount
API adapter provides legacy sensors during migration.
`v3/climate.py`: single climate HA entity reusing the old unique ID.

This bridge does not yet claim that V3 independently implements all legacy
authentication and polling protocols. It guarantees that those remain
available through one runtime boundary while modules migrate one by one.
The existing V2 scheduler and API logic remain physically present as a
transition dependency; they will be retired only after parity tests.

## Self learning and diagnostics

Only local read evidence can influence API route selection. A 200 with a
usable value is not proof a physical vehicle just refreshed. Currently V3
receives only **cached value present** hints from the V2 normalized state
and deliberately does **not** mark those fresh.

Three consecutive verified HTTP 404/410 results for the same
vehicle/operation may temporarily suspend an individual GET route for 24h.
401/403, 429, 5xx and missing fields do not disable capabilities. The
current passive bridge does **not yet inject request-specific HTTP evidence**
for this quarantine: that integration belongs to a later pilot gate.

No command route is automatically retried or switched after a failure.
Every result stays scoped locally to the vehicle; exported diagnostics
contain operation names and aggregate evidence, never VIN or raw responses.

## Acceptance and release gates

1. GitHub pytest and hassfest must pass on the **exact release SHA**.
2. Verify HACS installation and reconfigure V2 → V3 → V2 on the same HA
   config entry, ensuring the entry ID and primary climate entity IDs persist.
3. Test Q8 climate start/stop and vehicle readback on the physical vehicle.
4. Verify only one cloud poll per scan interval and no automatic wake action.
5. Review old quick-switch automations before choosing V3.
6. If green, publish a prerelease tag matching manifest version
   `3.0.0b1`, and install through HACS. If the GitHub connector has no
   release/tag publication action, publishing requires an explicit GitHub UI
   step; a version in `manifest.json` alone is not a release.

This first candidate is intentionally a **climate-only V3 vertical slice**,
not a generic API Workbench. The workbench comes after one complete
capability is verified end to end.



## GitHub Actions and HACS fork validation

The fork currently has `has_issues=false`, which caused the earlier HACS
metadata workflow to fail even when pytest and hassfest were successful.
Before publishing this candidate as a HACS prerelease, enable **Issues** in
the fork's GitHub repository Settings, then validate that the HACS check is
green. Existing older green commits are not evidence that V3 passed.

For HACS, simply editing `manifest.json` is not enough to distribute a
feature-branch build: HACS normally installs released versions or the
repository default branch. Do not move fork main/master to V3 just to make
this candidate appear. Publish a GitHub prerelease/tag for the exact tested
SHA only after release gates pass.


A known positive CARIAD `userCapabilities` verdict may enable the V3
climate entity even if the current status field is absent (control-only
mode); it will display an unknown state rather than falsely claiming
OFF. An explicit negative verdict suppresses a newly created V3 climate
control. The existing V2 engine's previously readable allowlisted
`climatisation` job flag is represented as historical evidence only,
not as a new fresh telemetry timestamp or proof of actuation.


## Documentation index

- [Why / What / How, ownership, clean architecture and extension](V3_ARCHITECTURE.md)
- [Reconfigure and test on existing Audi entry; rollback; HACS](V3_CONFIGURATION.md)
- [Acceptance test matrix and next capabilities](V3_TEST_MATRIX.md)
- [3.0.0b1 prerelease notes](V3_RELEASE_NOTES_3.0.0b1.md)

The experimental `v3_climate_experimental_unknown` option is OFF by
default. Explicit negative or impaired advertised support still blocks
control. Current model parser does not populate the `model_family` field:
the registry derives the Q8 hint only from verified Audi long/short model
metadata. User-defined nicknames are never authorizing evidence.


## Packaging gate versus beta acceptance

A HACS **test prerelease** is published only after pytest, hassfest and
HACS validation pass on its exact commit. Real Q8 operation and HA
V2→V3→V2 migration are *the purpose of that beta*, and remain acceptance
gates for stable promotion—not prerequisites to obtaining a test package.
