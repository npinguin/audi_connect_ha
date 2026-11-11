# Audi Connect V3 — Architecture baseline

**Status:** V3 climate beta candidate. **Scope:** one vehicle capability (`climate`) with optional status/control. **Branch:** `feature/v3-climate-pilot`.
**Architecture rule:** The same integration, login, account, vehicle registry and HA entities continue to exist. V3 replaces responsibility by vertical slice, **not** by parallel connector.

## WHY — from historical spaghetti to a maintained product

Audi Connect historically accumulates one-off changes for legacy MBB and newer CARIAD APIs: different URL templates, settings bodies, vehicle properties, platform entities and retry strategies. On one Q8 three UIs ended up addressing the same climate operation. The technical symptom is ownership drift: a control in `climate.py`, a duplicate quick switch, and services routing through independent conditions. A cloud 2xx may incorrectly appear as verified physical success, and a partial status poll can make a functional vehicle look unsupported.

V3 creates one supported concept (`Vehicle → Capability → [Status] + [Control]`) and a registry of context-specific API operations. The catalog and route selection are pure code, separate from HTTP, OAuth, HA coordinator and UX. V2 is retained as an **adapter / fallback** during an incremental migration. This is intentionally a small architectural seam, NOT a second vehicle product, scheduler or login stack.

## WHAT — the canonical owned objects

| Object | Canonical owner | One responsibility |
|---|---|---|
| Vehicle | Existing Audi Account / vehicle source | Identity, trusted metadata, authentication context; VIN never leaves local authenticated runtime |
| Capability | `v3/climate.json` | Stable semantic capability ID, optional status and optional control |
| API Family | `v3/climate.json`, executed by existing AudiService | Auth family and trusted region host policy, never arbitrary user URL |
| API Operation | `v3/climate.json` | Stable operation ID, HTTP method, relative route, response paths, optional context scope |
| Route selection | `v3/registry.py` | Resolve and explain applicable operations for one context |
| Runtime & evidence | `v3/runtime.py` | Single config-entry owner, per-vehicle local evidence, sanitized diagnostics |
| Polling / refresh | `v3/coordinator.py` → existing coordinator | Exactly one polling job and existing refresh callback |
| Control execution | `v3/climate.py` → existing account adapter | One user intent, exactly one known command, no auto retry |
| HA entity | `v3/climate.py` | One primary `climate.climatisation` with the existing unique ID |

A capability can be **status only**, **control only**, both, or (if neither applies) absent. Status/readability does **not** authorize a command. A model-name hint does **not** authorize a command.

## HOW — runtime ownership and zero-drift boundaries

1. The original HA Audi Connect config entry still owns the Audi credentials, device mapping and scan interval.
2. `runtime_version=v2` is the default. `v3_climate` selects the V3 coordinator **instead of** the old one, never alongside it.
3. The V3 coordinator uses the same `AudiAccount` adapter, including token refresh, rate limits, cloud fetching, post-action notify and all V2-only capabilities. It adds metadata processing on the returned data; no additional scheduled requests are issued.
4. V3 creates the **same** climate entity unique ID. It withholds an unverified target temperature slider and supports ON/OFF when a vehicle capability permits it. The overlapping quick switch is not created in V3; its historical registry entry is not deleted. Services are retained for backward compatibility; automation authors should migrate to the primary climate entity.
5. CARIAD status is the existing `selectivestatus` batch. Legacy MBB users remain on the original climate entity for now.
6. Commands use the reviewed V2 adapters but **V3 owns the selection policy**. For a trusted Q8 model, bodyless CARIAD start is the default. On other Auth0 vehicles, the existing vehicle-settings path is selected and refuses to submit a missing/unsafe stored temperature. A failed/unknown command is NEVER retried with another API variant.
7. A runtime option `v3_climate_experimental_unknown` may be enabled deliberately when Audi did not publish a capability inventory. Explicit negative and impaired capability verdicts remain blocked.
8. `V3Runtime.diagnostics` shows selected/rejected routes and evidence for anonymous local vehicle slots, never VIN, bearer tokens, coordinates or raw responses.

## Configuration hierarchy (simple by default)

```text
Audi integration (one account, one runtime mode)
  └── Brand catalog: Audi
       └── Capability: climate (status? + control?)
            └── Operations (MBB / CARIAD)
                 └── Optional scope: auth → region → vehicle_type → trusted model_family
```

No required per-model profile zoo. A vehicle receives the generic catalog by default. An optional, explicit scope restricts only the operation that needs it. A local vehicle can override selection via reviewed integration options without changing the shared definition. Unknown scope remains unknown: never infer a Q8 from a nickname.

The JSON catalog lives in the installed package. **V3 beta does not yet support live editing of arbitrary API templates**. Options already permit a known API variant; a future local Development Workbench may edit safe GET templates with schema validation, access control, and no mandatory HA redeployment.

## Learning — what is genuinely available in beta

- Existing normalized climate state may be a cached value; presence is recorded as `cached_present`, not as freshly measured.
- Existing previously readable allowlisted CARIAD jobs may be carried as *historical readable* evidence (never physical command success).
- `RouteEvidence` supports a 24-hour route quarantine after three consecutive **verified** 404/410 results. This beta has **not** yet connected request-specific HTTP status evidence to that classifier, so automatic route quarantine is **not active** in normal polling.
- 401, 403, 429, 5xx, stale timestamps and empty responses do not automatically label an Audi capability unsupported.
- Runtime safeguards may make unsupported commands unavailable. The historical climate entity remains in HA registry. Never delete user automations/history because a poll is incomplete.
- All local runtime evidence is transient. Community compatibility upload and per-model confidence aggregation are **not implemented**; the planned export will be privacy reviewed, explicitly opt-in, and limited to anonymized operation IDs, coarse context, outcomes and versions.

## Migration and backward compatibility

V2 → V3 Climate is an **integration option**, not an entity migration or new Audi account. V2 APIs and sensors continue to run. The same climate unique ID persists. Some old automations targeting `switch.climate_quick_control` will be unavailable in V3 and should be migrated to `climate.climatisation` **before** enabling it. Changing V3 → V2 causes the ordinary options listener to reload the integration and restores the historical V2 entity implementations. Historical Home Assistant entity/device IDs must not be renamed, re-registered or deleted.

The legacy temperature service and historical actions remain compatibility APIs for now; do not remove them in the V3 beta. New climate UI has no target temperature control on the Q8 until a target-write implementation has verified physical readback and full regression coverage.

## Extension contract — add a capability without growing spaghetti

Every next feature should be one new catalog capability, with optional status and control. It must declare:
- A stable semantic capability ID, value contract and owner;
- Reviewed operation IDs, **relative** URL templates, API family and optional scope;
- Response field/type/unit/timestamp, missing/partial/207 semantics, and error classification;
- Explicit read/passive polling owner; **no duplicate GET or poller**;
- User intent/authorization and confirmation policy for controls; no speculative retries;
- Entity unique-ID preservation, a V2 rollback path, and a contract test;
- Evidence criteria: readable HTTP != valid schema != fresh vehicle measurement != physical actuation;
- Minimal sanitized diagnostics and a community compatibility contribution format only after privacy review.

**Promotion gates:** Experimental → Candidate requires synthetic tests and live vehicle evidence. Candidate → Stable requires multiple API contexts, no extra polling, HA entity/service compatibility, failure-path coverage, HACS/hassfest/pytest checks, privacy audit and rollback. One model should not silently impose a route on every Audi.

## Explicit non-goals for beta

No generic dynamic HTTP executor; no arbitrary host/Authorization override; no auto-wake; no auto POST/PUT; no new trip, charge or health sensors; no wholesale V2 removal; no extra cloud polling; no central telemetry upload; no claim that request acceptance verifies car action.

## Engineering review checklist

Check the source of truth remains singular: no duplicated entity unique IDs; no new duplicate background jobs; exactly one account/session; no copied OAuth secrets in config; no undocumented fallback; errors and unavailable state are distinct; all fallback paths are real and tested; config options preserve user settings; docs/tests/manifest agree on version. PR review must reject drift rather than patch around it.


## One control-eligibility owner

`V3Runtime.control_verdict(vehicle)` is canonical for reported/impaired/unknown,
reviewed route selection and safe target preconditions. The HA climate entity
and diagnostics both use that decision, avoiding drift. In a mixed-vehicle
account, a globally selected Q8 operation not applicable to a second car
resolves to its context-appropriate reviewed default and records the reason.
This is **selection**, never a second command or a retry. Unavailable
vehicle-stored temperature makes settings-based control unavailable rather
than advertising a button that can only fail.


## Device-registry safety at V2→V3 configuration changes

The existing V2 helper `_async_cleanup_orphaned_devices` used to compare
registered devices with the current **in-memory** inventory. During a
disabled/failed first scan this can be empty and is not authoritative evidence
that the user removed every car. V3 therefore **never executes destructive
startup device cleanup**: registry removal is deferred until a separately
reviewed authoritative-inventory workflow is built. The V2 helper also
returns early when no active vehicles are known. Switching runtime modes
must not delete devices, history or automations.
