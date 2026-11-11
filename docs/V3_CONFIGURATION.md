# Audi Connect V3 — installation and configuration (3.0.0b4)

## Upgrade in place

Keep the current Audi Connect integration. Back up Home Assistant and make
note of existing V2 climate/charging automations. **Do not add a second Audi
Connect entry or delete the old entity registry.**

1. In HACS select the experimental `3.0.0b4` release from
   `npinguin/audi_connect_ha` and restart HA.
2. Open **Settings → Devices & Services → Audi Connect → Configure**.
   Choose `v3_climate` as Runtime generation and retain your cloud scan
   interval (minimum 15 minutes). Other V2 preferences are preserved for
   rollback but not used by V3.
3. The Audi vehicle device should show one climate entity, cloud last poll,
   vehicle age, V3 polling status, climate capability, and cloud refresh.
   Registered historical V2 entities may be listed as **disabled**; do not
   delete them.
4. If you need API experiments, enable **V3 Development Workbench** in
   Audi Connect Options while V3 is active (off by default). Reopen the
   integration after saving and open the **Audi V3 Development** sidebar
   item (administrator). Turning it off hides the panel but keeps tests.
   Select your existing Audi config entry and vehicle. Work with Climate
   Status / Start / Stop separately.
5. For Status click **Test GET**. The result includes the HTTP status,
   recognized field, vehicle capture timestamp and whether the mapping was
   usable. Accepted, valid, fresh reads may become the selected poll route.
6. For Control choose an existing CARIAD candidate or **Add experimental
   route** with a relative API path. Click **Test selected action** only when
   physically ready. Read the outcome and inspect the car/myAudi; click
   **Worked**, **Failed** or **Not sure**. V3 activates only a confirmed
   working route. Not sure keeps control testing blocked.
7. Once Start and/or Stop is confirmed, the primary climate entity exposes
   those controls. Unsupported features can be disabled independently.
8. Download Audi diagnostics for a privacy-safe view of which route works,
   cloud polling and capability status.

### Configuration location

- Integration Options: **runtime mode**, cloud polling interval, basic
  account/vehicle selection. No API route or body JSON fields in this wizard.
- Sidebar Workbench: **per-vehicle operation list**, relative URL, typed
  variables, JSON request body, response field mapping, test history and
  verified active selection. Changes are stored in HA `.storage` and do
  **not** require a code redeployment.
- Core code: approved authentication/host families and execution policy,
  version-controlled; changing a trusted host/security boundary requires
  a reviewed release, not a user template.

### Supported testing

CARIAD/Auth0 climate status is the first supported independent V3 poll.
The historical `vehicle_settings` climate start is not yet ported as a
safe V3 read-modify-write adapter; the old entry is shown as a candidate
but execution fails closed. The bodyless Start is restricted to trusted Q8
metadata. Other vehicle/API variants can be tested using explicit user
routes and controlled JSON bodies after inspecting their documentation.

**Important:** a cloud command accepted with HTTP 2xx is not a car
operation confirmed. Do not automatically try alternative climate
Start/Stop POSTs on timeout or uncertain feedback. V3 never wakes a parked
vehicle just to discover APIs.

### If V3 cannot sign in or discover the vehicle

Use the existing Audi credentials and Auth0 token. Verify V3 diagnostics
first; old V2 data should not suddenly appear under the V3 owner. Legacy
MBB is not yet migrated to the independent V3 engine. For any issue choose
`v2` in Options and reload. V2 will restore its previously disabled
historical entities. If setup itself fails, restore the previous known
working HACS package from the HA backup without deleting the Audi
configuration entry.

### Known beta limitations

- V3-only history currently covers Climate and cloud/core. Charging, trips,
  locks, mileage, oil and preheater remain accessible through V2 rollback.
- Self-configure mode with *automatic sequential control tests* is a later
  assisted feature, after user authorization and proven safe stop rules.
- The dashboard's route editor accepts a JSON definition for advanced users;
  a visual route-builder and shared community anonymized compatibility data
  are planned, not shipped in b2.
- No physical Q8 test is implied by green CI. The first tester must record
  actual action completion, source freshness and API call budget.

**No extra accounts, no entity deletions and no automatic actuator retries.**


### Candidate save versus activation

The Workbench offers **Save candidate** to remember the currently chosen
route for the selected vehicle and aspect. It persists across HA restarts
without executing or activating the route. **Activate verified path** is a
separate action available only after a valid, recent status GET or user-
confirmed physical control test. An untested or stale route is never
silently enabled.

A **Capability Status** section lists each known V3 attribute/control,
its family, template route, measured result and selected state. Additional
read-only job paths inherited as **V2 references** are explicitly marked
`known_v2_not_migrated`. These entries are migration candidates, not
claims that those APIs are working in V3.

### V2 configuration and rollback

The Options dialog preserves original V2 flags and local dealer metadata
when switching runtimes. V3-only workbench controls are off in V2; returning
to V3 does not delete custom API profiles or route test history.
