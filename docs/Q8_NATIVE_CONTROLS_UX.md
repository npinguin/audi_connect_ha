# Q8 one-screen Home Assistant controls (b8)

**Proven in owner's b7 live test:** Lock, Unlock, climate ON, climate OFF,
and Flash lights all physically work. These are separate from HTTP acceptance.
This is a UI improvement on top of the unchanged, proven CARIAD routes.

## One control per reversible function

- **Climate — ON/OFF switch**: new `switch.*climate_quick_control` named
  *Climatisation ON/OFF*. It calls the exact proven bodyless
  `start_climate_control(vin)` on ON, and
  `set_vehicle_climatisation(vin, False)` on OFF. It is backed by the Audi
  `climatisationState`; it NEVER reports a change merely because HTTP 200
  occurred, and it does not execute a second poll (the account already notifies
  the HA coordinator). Existing climate entity still offers temperature control.
- **Doors — one native lock entity**: the existing `lock.*` is the correct
  Home Assistant abstraction for Lock and Unlock. Tap it to open HA's native
  lock/unlock control. A generic `switch` for security-critical unlocking
  would duplicate the same command, lose lock semantics and invite
  accidental unlocks. Existing entity unique ID is unchanged.
- **Flash** remains a button, not a toggle.
- Existing Start/Stop climate buttons are preserved for existing
  automations; they are not the recommended main dashboard controls.

## Dashboard — two practical HA-native tile cards

Replace these placeholder IDs with the actual entity IDs from
Settings -> Devices & services -> Audi Connect -> Devices -> Q8 -> Entities.

```yaml
type: grid
columns: 2
square: false
cards:
  - type: tile
    entity: switch.REPLACE_WITH_CLIMATE_QUICK_CONTROL
    name: Climate
    features:
      - type: toggle
    tap_action:
      action: more-info
    icon_tap_action:
      action: toggle
  - type: tile
    entity: lock.REPLACE_WITH_Q8_DOOR_LOCK
    name: Doors
    tap_action:
      action: more-info
    icon_tap_action:
      action: more-info
    features:
      - type: lock-commands
```

Home Assistant's native lock more-info dialog has a single stateful
lock/unlock control; the optional lock-commands feature additionally exposes
explicit Lock / Unlock buttons. Unlock should not be silently triggered by
an accidental tap on an ordinary on/off light-style switch.

## State and safety

The car can take time to report the new physical state. The climate switch
shows the latest car value until new telemetry arrives; a failed command
raises an HA error. It never optimistically lies or repeats remote commands.
This is particularly important with Audi rate-limit HTTP 429.

The quick climate ON command intentionally uses the settings already saved
in the vehicle, not a temperature picked from the HA climate card. To change
temperature, use the existing climate entity and verify the result.

## Volkswagen ID.4

The dashboard interaction pattern can be reused on any HA vehicle that has a
real stateful `climate` / `switch` / `lock` entity. The **Audi backend and
OAuth cannot be reused for an ID.4**: a Volkswagen-brand account and
Volkswagen service permissions are required. As of 2026-11, upstream
VW Group Connect documents European VW MEB ID.4 as *read-only* due to VW
blocking the modern two-way auth. Do NOT advertise an ID.4 climate/door
toggle unless a functioning brand-native command endpoint is verified.
The user's existing `vag_connect` can expose telemetry independently;
Mobility can consume both brands through their HA source entities.

Reference:
- https://www.home-assistant.io/dashboards/features (toggle and lock-commands)
- https://contributors.home-assistant.io/design/more-info/lock/
- https://github.com/its-me-prash/vwgroup-connect-ha
