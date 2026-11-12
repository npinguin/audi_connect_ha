# Audi Connect V3 — Development profiles and fast discovery

**Historical implementation notes and target policy.** For current architecture and the closure backlog, see [architecture](V3_ARCHITECTURE.md) and [closure plan](V3_ARCHITECTURE_CLOSURE.md). The sections describing b2/b3 are historical, not the target.

**Architecture decision:** only shared HA integration configuration and Audi
authentication belong to both V2 and V3. API engines, discovery, polling,
capability models, control dispatch, diagnostics and devices are V3-owned.
V3 development has an opt-in Workbench in experimental HACS prereleases; this does not imply stable real-vehicle acceptance.

## Development phase (NOW): explicit API experimentation

A developer can introduce a route under the generic Audi catalog, scoped
to the selected vehicle rather than duplicating brand/model profiles.

| Concept | Input / behavior |
|---|---|
| Capability | `climate`, with optional `status` and `start/stop` controls |
| Operation | Stable ID `user.climate.start.*`; unique within the vehicle profile |
| API family | CARIAD Auth0 or legacy MBB; family owns trusted host and auth |
| Request | GET status / POST action, relative path such as `/vehicles/{VIN}/climatisation/start` |
| Parameters | Typed variables, e.g. `MODE: string`, `TARGET: integer` |
| Body | JSON template; whole `{TARGET}` yields a typed integer, not string interpolation |
| Optional profile refinements | Auth / region / vehicle type / model family |
| Evidence | Untested, HTTP accepted/rejected, human-confirmed Worked / Failed / Unsure |
| Active configuration | User can select **only confirmed working routes** for that control |
| Disabled | Start or Stop individually disabled, independent of climate status |

The route compiler rejects absolute URLs, unknown API families, auth
overrides, undeclared placeholders, non-relative vehicle paths, malformed
JSON and executable templating. The resolved host and bearer token stay
with the reviewed V3 API engine and are never supplied by the developer
as arbitrary request headers.

`v3/development_profiles.py` is a **pure configuration model** with
`add()`, `preview_request()`, `begin_test()`, `observe_http()`,
`confirm()`, `choose_working()`, `disable()` and `snapshot()`.
It does not execute a request or persist secrets. The clean V3 runtime now connects this model to a native opt-in Workbench and
HA storage, preserving candidate choices and evidence separately from controls.

### Example development route

```json
{
  "id": "user.climate.start.custom_body",
  "capability": "climate",
  "aspect": "start",
  "family": "cariad",
  "method": "POST",
  "path": "/vehicle/v1/vehicles/{VIN}/climatisation/start?mode={MODE}",
  "variables": {"MODE": "string", "TARGET": "integer"},
  "body": {"targetTemperature": "{TARGET}", "enabled": true},
  "scope": {"region": "DE"},
  "description": "Developer experiment"
}
```

This is illustrative only; it does not assert Audi supports the example
mode query or JSON shape. The user must deliberately test the route and
confirm physical behavior before choosing it as the vehicle's active control.

## End-user phase (TARGET): automatic fast discovery

Superseded design: automatic sequential physical control tests are not the end-user onboarding mechanism. Reviewed engineering evidence and applicable local bindings are used for automatic, bounded read-only fast discovery. Known eligible controls are automatically exposed without manual per-control testing; unknown controls remain unavailable. No automatic physical action, wake, mutating retry or speculative route fallback. See [ADR 002](V3_ADR_002_FAST_DISCOVERY.md) for the binding and activation policy. Engineering and normal HA commands use the same persistent lifecycle in the target.

## Outstanding implementation gates

1. Dedicated V3 dispatcher and API discovery engine, not imports from V2
   cloud request logic;
2. Local HA persistence and a configurable native Development Dashboard;
3. Verified operation request rendering and an explicit dispatch permission;
4. Separate status evidence, HTTP evidence, *fresh* readback and user feedback;
5. Per-vehicle activation into the V3 entity without changing other vehicles;
6. HACS/pytest/hassfest + real Q8 acceptance before publishing another release.

**Do not infer physical vehicle acceptance from green synthetic CI.**


## GET evidence and active route selection

Status GET operations are handled with `record_status()`: evidence records
HTTP status separately from schema correctness and field freshness. Only a
2xx response **with valid schema and fresh data** can become the selected
polling route via `choose_working("climate", "status", operation_id)`.
A 429, authorization failure or cloud outage is inconclusive, not a
permanent capability denial. If a selected route later fails, its
selection is withdrawn until a new confirmed result.

All operation evidence is represented in the local `snapshot()` structure.
`v3/profile_store.py` now provides a V3-owned private Home Assistant Store
adapter and validated restore operation. Partial vehicle inventories must not
erase other cars' profiles. The adapter is wired into the current clean V3 runtime. 3.0.0b1 used a
historically different runtime architecture. This representation must never be mistaken for a sanitized
community export: custom user-authored descriptions and relative routes may
contain their own sensitive literals and require privacy filtering.


## b3 Workbench UI and selection persistence

The Workbench has a **Save candidate** operation separate from **Activate
verified path**. Draft selections are persisted in a dedicated field of the
vehicle-scoped profile and restored from HA Store without authorizing
untested controls. Selection is preserved while choosing alternatives in
the dropdown and across UI refresh/reload.

The **Capability Status Dashboard** lists V3 catalog attributes and
controls with family, route, result and selection. Historical V2 read-only
job names/potential GET paths are included only as `known_v2_not_migrated`
references for the next engineer to systematically validate. They are
not automatically probed or advertised as working.
