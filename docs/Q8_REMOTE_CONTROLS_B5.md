# Audi Connect v2.5.3b5 — Q8 remote command feature/fix beta

## Functional changes

- **Door lock/unlock (Auth0)**: modern CARIAD POST access/lock and access/unlock with the configured Audi S-PIN in a JSON request. Legacy RLU remains for legacy logins only. No unsafe automatic retry or fallback. Confirm via pendingrequests if a request ID is supplied.
- **Direct climate buttons**: Start climate (car settings) and Stop climate appear on the existing Audi vehicle HA device. Start sends a bodyless climatisation/start request using the climate settings stored in the car; this is intentionally not the HA temperature value.
- **Backward-compatible climate automation**: execute_vehicle_action with start_climatisation is routed to the modern climate start instead of the deprecated legacy start.
- **Error propagation**: lock, climate, charging actions and direct services now report explicit False failures to Home Assistant rather than silently accepting them.
- **Valid HTTP acknowledgements**: modern command handlers can handle 204 No Content and HTTP 200 with an empty response. pendingrequests 204 is not a rejection. The vehicle's physical response still must be verified.
- **Privacy**: diagnostics use fixed modern_access / legacy_access categories and HTTP status, without VIN, S-PIN, token, request body or raw response.

## HACS test procedure

1. Back up Home Assistant. Keep the existing Audi config entry and unique entity IDs.
2. In your HACS custom repository npinguin/audi_connect_ha, select pre-release v2.5.3b5. Restart Home Assistant.
3. On Audi Q8 device: locate existing Door lock entity and new Start climate (car settings) / Stop climate buttons.
4. Confirm Audi S-PIN is configured locally; do not include it in shared logs.
5. While physically near your parked car, test Lock, then Unlock. Check actual doors, myAudi command history, and Home Assistant response. Do not repeatedly unlock unattended.
6. While parked, test Start climate (car settings), physically verify the vehicle starts heating/cooling, then Stop climate. The command uses car-stored settings, not the value shown on the HA climate card.
7. If temperature-setting mode on the HA climate card fails, enable optional Quick start climate using car-stored settings in Audi options to use the same bodyless start.
8. Export diagnostics after the test. It includes route categories, statuses and freshness. Never share HAR cookies, credentials, PIN or tokens.

## Known limits

- 200/202/204 from CARIAD can mean gateway acceptance, not proven physical operation.
- Permissions may be denied per vehicle, model year, region, equipment or account role.
- This release does not claim to fix chargingProfiles job errors or activate auxiliary heating / remote engine start.
- Code and tests are checked in CI; live testing of Q8 commands remains essential before claiming functionality works.
- Development branch fix/q8-modern-remote-commands stays available for continued debugging.

## References

- https://github.com/audiconnect/audi_connect_ha/issues/903
- https://github.com/audiconnect/audi_connect_ha/issues/766
- https://github.com/audiconnect/audi_connect_ha/issues/873
- https://github.com/acfischer42/CarConnectivity-connector-audi/
