# Audi Connect Q8 — feature parity against CarConnectivity-connector-audi

Reviewed 2026-11-10. Reference: https://github.com/acfischer42/CarConnectivity-connector-audi (default main, MIT, Copyright 2025 Achim Fischer). This is a **feature comparison**, not a wholesale source-code port. Our implementation remains native Home Assistant / Audi Connect, with a different (currently working) Auth0 login and different device/entity identifiers. We acknowledge the reference project; all new adapters are independently authored.

Legend: **Existing** = already in b7; **b8** = added in this iteration; **Experimental** = requires explicit options toggle and model capability, and needs physical acceptance; **Gap** = not claimed.

| Reference area | Home Assistant Audi Connect | Status / limitations |
|---|---|---|
| OAuth and session caching | Browser Auth0/PKCE + refresh, separate from legacy flows | Existing; do NOT copy source's older username/password authentication |
| Vehicle enumeration / type | VIN-bound entities and model/year/fallback | Existing |
| Vehicle pictures | Not mapped to HA device picture | Gap; external connector has raw vehicle_images, no trustworthy image field known for Q8 |
| Online / active readiness | Vehicle reported connectivity and activity sensors | b8; values from readinessStatus, not HA cloud connection |
| Capability inventory and service health | 72 Q8 capabilities; capability-aware polling and diagnostics | Existing b7 |
| Odometer | Mileage sensor | Existing |
| Hybrid fuel and electric ranges | Fuel/SOC, charging, primary/secondary range | Existing |
| Fuel level, low battery 12V | Fuel present; detailed 12V battery condition not mapped | Existing + Gap |
| Doors/boot and windows states | Door/window/lock sensors | Existing; all values depend on vehicle model |
| Door Lock and Unlock | Modern CARIAD Auth0 access endpoints with local S-PIN | Existing; Lock AND Unlock physically confirmed on owner's b7 test |
| Parking GPS | HA-native device_tracker with parked-position capture and age | Existing; parked fix, not continuous phone-like GPS |
| Park Time | Legacy parking clock or estimated parked-position capture | Existing b6 |
| Vehicle lights status | Current light/sensor fields | Existing |
| Flash / honk | Flash lights working; horn deliberately not enabled | Existing + Gap; avoid accidental horn |
| One-tap climate quick control | A stateful native HA switch using proven car-settings start and stop | b8; real car state, no speculative toggle, no duplicate polling |
| One native door lock control | Existing native lock entity, HA Lock/Unlock dialog or tile command feature | Existing, no duplicate generic lock switch |
| Charging SOC/power/state/rate/plug | HA sensors and active controls | Existing; actual car capability varies |
| Charging limits | Numeric AC current, categorical current mode | b8 read-only |
| Plug auto-unlock setting | Car-reported on/off setting | b8 read-only |
| Target SOC | Existing sensor/number CARIAD charging/settings | Existing, writes unproven on Q8 |
| Start/stop charging | Modern CARIAD charging/start, charging/stop | Existing service; b8 opt-in direct buttons; not physically validated |
| Charge mode/profiles/timers | Existing HA entities for modes/profiles/timers | Existing; `chargingProfiles` API job fails on owner's Q8 |
| Climate start/stop | Direct bodyless start and stop buttons | Existing, physically confirmed |
| Climate settings/temp/zones | Target temperature, window heating option, front/rear zones | Existing (car-specific) |
| Climate timers | Count, next enabled local time, bounded timer attributes | Existing b7; read-only and timezone not guessed |
| Window heating status | Existing read fields / climate setting | Existing; vehicle dependent |
| Window heating start/stop | Modern CARIAD windowheating/start, /stop | b8 experimental, not verified on Q8 |
| Wake vehicle | Modern vehiclewakeuptrigger, user-triggered only | b8 experimental; no automatic retry or wake on poll |
| Maintenance inspection / oil service | Car-reported days/km and service overview | Existing + b8 |
| Local preferred dealer | Native Configure multi-car form + visible sensor | b8 manual only; no verified CARIAD dealer lookup |
| Local warranty / appointment | Per-vehicle HA option data, same Configure flow | b8, never labeled Audi cloud data |
| Trip data / driving history | Not implemented with modern Auth0 | Gap; requires separate Trips API/entitlement evidence |
| Remote auxiliary heating | Legacy or missing API, not provisioned in Q8 probe | Gap; don't confuse with working electric climate |
| Remote engine start | PHEV Q8 fail closed | Deliberately excluded for safety |
| Raw API export / external MQTT framework | Not included; HA has native entities and RHI Mobility | Deliberately excluded to avoid duplicate device/auth stack |

## Important acceptance gates

1. No regressions: physical climate start/stop, unlock and flash lights.
2. Physical Lock and Unlock were confirmed on b7; still do not report HTTP 200 as success without real state; one post-action refresh maximum; respect 429.
3. Local dealer shows 'Not configured' until configured; Configure -> edit dealer -> choose car -> save; update options without deleting normal scan settings.
4. Additional read-only sensors are backed by explicit CARIAD source fields and return unavailable/unknown when absent; false is not 'missing'.
5. Experimental remote commands are OFF by default; require both opt-in and reported capability. They are never called by background polling.
6. No duplicate entities or removal of old unique IDs; do not introduce a second CarConnectivity runtime or login.
7. HACS prerelease CI: pytest and hassfest PASS. Repository Issues setting may still block independent HACS metadata check.

## Upstream strategy

After live Q8 acceptance, separate portable read-only model/status improvements, dealer UI (local only), and genuinely tested remote command changes into upstream PRs. Do not describe the Lock mutation as fixed until the vehicle physically locks. Keep original project's copyright/license notices when any substantive source is actually reused.
