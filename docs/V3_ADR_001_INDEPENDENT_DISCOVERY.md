# Audi Connect V3 — ADR 001: Independent Discovery & Assisted Actions

Status: **Implemented in V3 3.0.0b2 source; real-vehicle acceptance pending.**
This ADR supersedes the old shared-V2-polling architecture. See
[V3_ARCHITECTURE.md](V3_ARCHITECTURE.md) for the current code and support
scope. The published 3.0.0b1 remains historically unchanged.

## WHY

The first V3 beta still inherited the full V2 coordinator, API adapter, entity
platforms and Options wizard. With V3 enabled, 82 entities could remain present
and an API variant selected in the global wizard could mismatch a vehicle.
This violates the desired clean vehicle model and prevents safe experimentation.

## Ownership (hard boundary)

| Shared between V2 and V3 | Owned exclusively by V3 |
|---|---|
| Audi authentication / token provider | API request engine (with scoped approved hosts and bearer use) |
| HA integration config-entry and credential storage | API discovery, refresh scheduler, rate budget and freshness |
| HA entity registry, preserving unique IDs | Capability catalog, profiles, route resolver and test evidence |
| None of the V2 API dispatch logic | Entities: Refresh, Cloud Poll, Climate Status & Control |
| None of the V2 polling or domain models | Development Dashboard, diagnostics and optional community export |

**One runtime at a time per integration entry.** V2 must not be secretly
running inside V3. Existing V2 business logic can be studied or reused as
design evidence, not imported as V3 runtime dependencies. No destructive
device/entity registry cleanup on V2→V3. Only HA auth/config are shared.

## WHAT — vehicle capability discovery

```text
Audi integration / shared authentication + configuration
  V3 Vehicle
    Core (cloud connectivity, refresh, API rate budget)
    Capabilities
      Climate
        Status?  -> automated GET discovery + chosen poll route
        Control?
          Start  -> guided action discovery
          Stop   -> guided action discovery
```

The default global brand catalog lists alternative operations. Optional
auth/region/vehicle family refinements narrow the choices only where needed.
No mandatory profile per Q8, e-tron, BEV, region or model year. Working
evidence is local to one vehicle; configurable, versioned refinements can later
be contributed to a privacy-reviewed shared community profile.

## HOW — two discovery policies

**Status GET discovery:** try the most likely read-only route within rate
limits and bounded attempts; classify HTTP, payload schema, mapping and
freshness independently. On repeat evidence a non-working route is temporarily
excluded. A working route becomes the selected regular cloud polling route.
One selected status poll, no parallel V2 poll. Missing 207 fields, 429,
timeouts and sleeping vehicles do not mean unsupported. Avoid proactive wake.

**Control discovery (user assisted):**

1. Show a ranked list of current known variants, including parameter schema,
   applicability, test history and a Disable option.
2. The user intentionally clicks **Test Start** or **Test Stop** once. V3
   dispatches at most that one selected operation.
3. Show transport result, sanitized response shape and, when available, fresh
   vehicle readback. HTTP 200/202 alone is `accepted_unconfirmed`.
4. Ask the user **Worked / Failed / Not sure**. Worked/Failed requires
   verifying actual vehicle state. Not sure blocks further action variants.
5. If failed, offer the next compatible option, but only on a **new,
   explicit user action** and respecting cooldown. No automatic POST retry.
6. Save the user-confirmed working variant as this vehicle's preference;
   allow separate disablement of Start and Stop. A disabled control must not
   disable a readable climate status.
7. Later, a user may define/customize an action: relative API path with
   placeholders such as `{VIN}`, constrained method, typed parameters,
   request template, response mapping and readback policy, using approved
   authentication/host profiles. Custom endpoints remain experimental until
   tested; never allow arbitrary external hosts or expose auth tokens.

## Implementation ownership and rollout

`v3/action_discovery.py` implements a **pure**, non-network guided-action
state machine. It supports explicit attempt lifecycle, HTTP observation,
human confirmation, per-vehicle choice, cooldown, disablement and redacted
result snapshots. It **does not yet dispatch commands, persist profiles or
render a HA dashboard**. The persistence and frontend belong to the V3
runtime/application boundary; do not write these responsibilities into the
climate entity.

Implementation sequence:
1. New V3 auth facade reading shared HA credentials;
2. Own API dispatcher, status discovery and rate-aware coordinator;
3. Limited V3 entity platforms and non-destructive V2→V3 registry migration;
4. Local development dashboard with guided action test wizard and profile
   persistence, including custom templates only when separately reviewed;
5. One real Q8 live validation; new pre-release with full pytest, hassfest,
   HACS checks and rollback tests.

A physical action's outcome is never inferred solely from an API response.
All actions require an explicit initiating user gesture. Automatic GET route
learning and opt-in contribution of anonymized evidence can improve over time,
but the system must remain usable with zero manual profile configuration.
