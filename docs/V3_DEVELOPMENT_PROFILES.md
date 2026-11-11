# Audi Connect V3 — Development route profiles and later self-configuration

**Architecture decision:** only shared HA integration configuration and Audi
authentication belong to both V2 and V3. API engines, discovery, polling,
capability models, control dispatch, diagnostics and devices are V3-owned.
This is new clean-development code, **not** a released HACS dashboard.

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
It does not execute a request or persist secrets. A native Home Assistant
Development Dashboard and HA local-storage adapter must connect these
methods to authorized controls. Selected routes and evidence must persist
per vehicle and V3 capability; this library provides serialization-compatible
snapshots but does **not** yet claim reload persistence.

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

## User-testing phase (LATER): one-click self-configuration

The user asks **Configure Climate** and explicitly authorizes a bounded
guided discovery session. V3 ranks known context-applicable candidates
from the global catalog plus local profile history, beginning with the
most likely. One candidate runs at a time.

For status GET, automatic retry can proceed within the cloud rate budget
when the response is objectively invalid and no vehicle action is involved.

For climate control POST, automated progression is permitted only after
a trustworthy fresh vehicle observation **proves no action occurred** (or
the user supplies the missing physical confirmation). HTTP error, a 2xx
response, timeout or stale cached climate state alone does NOT prove the
previous attempt did nothing. Such an ambiguous result pauses the
one-click flow and asks the user to verify before any second POST.

Once physical success is confirmed, the winning operation and its parameters
are saved to that vehicle's local profile. Maximum attempts, cooling periods,
account-level cloud budget, cancellation and rollback apply. No silent
global promotion to every Audi. If nothing works, the capability/control
is disabled and diagnostics expose the tested options and results.

## Outstanding implementation gates

1. Dedicated V3 dispatcher and API discovery engine, not imports from V2
   cloud request logic;
2. Local HA persistence and a configurable native Development Dashboard;
3. Verified operation request rendering and an explicit dispatch permission;
4. Separate status evidence, HTTP evidence, *fresh* readback and user feedback;
5. Per-vehicle activation into the V3 entity without changing other vehicles;
6. HACS/pytest/hassfest + real Q8 acceptance before publishing another release.

**Do not treat this model-only branch as a working HACS test release.**


## GET evidence and active route selection

Status GET operations are handled with `record_status()`: evidence records
HTTP status separately from schema correctness and field freshness. Only a
2xx response **with valid schema and fresh data** can become the selected
polling route via `choose_working("climate", "status", operation_id)`.
A 429, authorization failure or cloud outage is inconclusive, not a
permanent capability denial. If a selected route later fails, its
selection is withdrawn until a new confirmed result.

All operation evidence is represented in the local `snapshot()` structure,
but only the application-layer HA Store integration will make it persistent
across restarts. This representation must never be mistaken for a sanitized
community export: custom user-authored descriptions and relative routes may
contain their own sensitive literals and require privacy filtering.
