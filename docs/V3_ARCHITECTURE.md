# Audi Connect V3 — Why / What / How (3.0.0b2)

**One Audi Connect integration, one config entry, one active runtime.**
V2 is the rollback choice. **Only login/token handling and integration
configuration are shared.** V3 has its own transport, polling, vehicle state,
capability catalog, profile store, entities, diagnostics and Development UI.

## WHY

Earlier versions evolved through model-specific fixes and overlapping V2
climate controls. Our first V3 beta (3.0.0b1) made a new climate entity but
still loaded V2 polling and roughly 82 registered entities. This is not the
desired product architecture. The new V3 must be clean, lean, evidence-based
and expandable without redeployment of every experimental route.

## WHAT — ownership table

| Single owner | Responsible for | Source |
|---|---|---|
| Integration (shared) | HA entry, region, scan interval, Audi refresh token | `config_flow.py`, `v3/auth.py` |
| V3 Auth Facade | invoke existing Audi OAuth token exchange only | `v3/auth.py` |
| V3 API Transport | approved CARIAD/GraphQL hosts, HTTP request, quota guard | `v3/transport.py` |
| Vehicle inventory | GraphQL discovery and trusted manufacturer model hint | `v3/vehicle.py` |
| Capability Catalog | Climate → Status? + Control.Start? + Control.Stop? | `v3/climate.json`, `v3/registry.py` |
| API Discovery & Poll | GET path selection, schema, freshness, observed evidence | `v3/engine.py`, `v3/coordinator_clean.py` |
| Action Evidence | human-initiated tests, response, physical outcome, disabled path | `v3/action_discovery.py` |
| Profiles & Store | per vehicle custom routes, verified active choices, rollback | `v3/development_profiles.py`, `v3/profile_store.py` |
| HA Entity Projection | one climate + cloud/age/capability/poll sensors + refresh button | `v3/entities.py` |
| Development UX | route editor and assisted test/selection, administrator only | `v3/dashboard.py`, `v3/frontend/panel.js` |
| HA registry migration | non-destructive reversible disable of old entities | `v3/registry_lifecycle.py` |

The legacy modules remain in the package for V2 rollback; **V3 never calls
`AudiAccount.async_refresh_data()`**, V2 platform logic, V2 vehicle command
dispatch or the V2 data coordinator. The existing OAuth code is deliberately
reused as the shared authentication boundary rather than rewriting PKCE and
token rotation independently. V3 transport uses its own HTTP flow.

## HOW — simple model, optional refinement

```text
Audi account (shared auth + config)
  └─ V3 vehicle (trusted Audi metadata / Auth0 / region)
      ├─ Cloud / Refresh (own budget and scheduler)
      └─ Capability: Climate
          ├─ Status (optional)
          │   └─ GET operation alternatives, schema, car timestamp
          └─ Control (optional)
              ├─ Start → candidate POST paths
              └─ Stop  → candidate POST paths
```

The brand catalog provides generic operations. An operation can optionally
be scoped by authentication family, region, vehicle type or verified model.
One car with an unknown model does not require an invented Q8 profile.
Custom development operations can be added to the selected car's private
overlay, referencing the known API family. A user cannot provide an
arbitrary external host, Authorization token or executable template.

A status GET may be tested automatically and the working path selected
when the HTTP response, expected field and freshness evidence are valid.
A 404 may justify trying a different GET; 401/403/429/5xx are inconclusive
cloud/auth/rate errors, not definitive missing capabilities. In normal polls
V3 never sends proactive wake or sends parallel V2 requests.

A control POST is **different**: the user explicitly chooses Test and a
single candidate, reviews the response, then confirms whether the physical
vehicle actually did something. Only a confirmed working route can be
activated. HTTP 200/202 is merely `accepted_unconfirmed`. Uncertain
attempts remain blocked across a restart. Control alternatives cannot be
blindly retried on timeout. Per-vehicle Start and Stop can be disabled
independently of Status.

## Active HA surface in beta b2

In V3 mode the integration forwards only the Climate, Sensor and Button
platforms with V3-specific setup. A single vehicle presents:
- one existing-identity `climate.climatisation` (no unverified temperature slider);
- Cloud last successful poll (existing identity);
- Vehicle data age (existing identity);
- V3 cloud polling (new);
- Climate capability state (new);
- Refresh Audi cloud button (new, read-only GET, not a vehicle wake command).

Historical V2 registry entries are **disabled by the integration** and tracked
in private HA storage, not deleted. Only entries disabled by this migration
are re-enabled when switching back to V2. No guessing based on an incomplete
vehicle inventory. V3 keeps the historical climate unique ID and car device
identifier. Registered counts may still include disabled historical entries;
the actively loaded entity list is minimal.

## Architecture safeguards

1. Exactly one V2 or V3 coordinator per HA entry.
2. A single canonical selection and evidence store per capability/vehicle.
3. No control command retries or automatic wake.
4. A cloud HTTP 2xx is not a fresh car timestamp or physical confirmation.
5. Read-modify-write operations must have independently proven body
   preservation before enabling. The old settings climate start is not
   silently treated as bodyless; user can add a reviewed custom POST.
6. V2 entity unique IDs and historical user-disabled state are preserved.
7. No tokens, VINs, raw bodies or locations in exported V3 diagnostics.
   The local admin Workbench uses its own authenticated vehicle IDs.
8. Non-Q8 and legacy MBB contexts are not assumed to share Q8 actions.
9. Full regression CI + hassfest + HACS packaging for every prerelease.

## Historical capabilities — progressive migration in ONE PR

1. **b2:** independent Vehicle/Cloud + Climate status/control pilot + API
   Development Workbench. Validate against Q8 with realistic state/readback.
2. **Next:** charging telemetry (SOC, charging state/mode/rate/plug) from
   selected CARIAD jobs with existing HA unique IDs.
3. **Then:** verified charging controls with clear start/stop/target SOC
   semantics, no destructive partial settings writes.
4. **Then:** vehicle access & health (lock, doors, windows, range, mileage,
   service, oil) with optional status/control capabilities.
5. **Then:** short/long/last trip and consumption data with OEM schema
   checks, timestamps, units and unchanged IDs.
6. **Finally:** region-specific legacy MBB support, wake and miscellaneous
   historical functions only after independent safety/evidence gates.

No duplicate V3 branches or PRs per capability. Subsequent commits go to
`feature/v3-clean-discovery` / PR #20. Historical functions stay available
in **V2** until individually migrated; they do not leak into V3.

## Release acceptance

`3.0.0b2` is an **experimental HACS prerelease**, not a production migration
claim. Exact-SHA Python/hassfest/HACS checks gate publication. Real car
acceptance remains separate: verify login, Q8 discovery, cloud timestamps,
climate GET, one guided start/stop, physical readback, HA entity count,
V2→V3→V2 rollback and cloud budget. Report failures with privacy-safe
diagnostics; do not publish full raw Audi responses or VINs.
