# ADR 002 — Engineering discovery and automatic fast discovery

**Status:** accepted target direction, not fully implemented. Date: 2026-11-12. Supersedes the assumption in ADR 001 / older beta documentation that each end user must manually test each control before activation, and any proposal to automatically sequence physical actuator tests. ADR 001's independent runtime and no blind mutations remain binding.

## Decision

Two modes of the same capability and command engine, not two runtimes.

| | Engineering discovery | End-user fast discovery |
|---|---|---|
| Audience | Administrator/engineer, opt-in Workbench | Every normal installation |
| Status | Bounded read-only experiments | Automatic bounded read-only discovery |
| Control route | Explicit test of one selected candidate | Automatic resolution of known applicable routes |
| Physical action during discovery | One deliberate user-authorized test; physical review | None |
| Evidence | Local per-vehicle, reviewable, versioned | Reviewed catalog rule or applicable verified local binding |
| Activation | Verified candidate after review | Automatic if evidence and current eligibility are sufficient |
| Unknown route | Remains experimental | Unavailable/unknown; no guessing or forced Workbench |
| Execution | Same Command Engine | Same Command Engine for actual HA requests |

Fast discovery means identifying and enabling the correct control entity automatically, NOT automatically operating a lock, charger, heater, horn, engine or wake endpoint. A GET-like operation with side effects is not a discovery read. GraphQL inventory queries may use POST transport only as a reviewed, strictly read-only query; no GraphQL mutations or generic POST exceptions.

## Engineering workflow

1. Select VIN, capability/command and candidate operation; validate family, context, typed parameters and security classification.
2. Explicitly authorize that exact action and parameters. S-PIN is injected from secure configuration only where the code-owned handler permits it.
3. Persist pending attempt; execute at most one mutating operation. Backend acknowledgment is not proof of physical effect.
4. Perform bounded confirmation/readback where possible; engineer records worked/failed/uncertain after actual inspection. Uncertainty blocks blind alternative attempts.
5. Save a local binding only after sufficient evidence. A parameterized binding stores its validated schema and defaults where applicable, not a stale per-test argument or secret.
6. Promote evidence into a reviewed catalog rule using tested route/schema revision, applicability scope, prerequisites, model/market/auth/API generation when relevant, evidence provenance and known exclusions. Do not infer fleet-wide compatibility from one Q8. Community evidence remains advisory until reviewed. Never publish VINs, credentials, raw responses or private location data.

## Automatic fast-discovery algorithm (target)

At first setup and subsequent startup, restore profiles and obtain inventory using the existing authenticated account. Read the normal selective-status batch and advertised/impairment capabilities. Reuse responses, do not duplicate calls solely for discovery. Include approved bounded MBB reads where applicable. A user does not need to visit the Workbench.

For each capability, attribute and command:

1. Resolve candidate operations against catalog and trusted vehicle context (VIN-local identity, API family/auth, region, known model metadata where required, advertised capabilities, required attributes and security restrictions).
2. Prefer a current, locally verified binding for the exact vehicle and operation revision. Otherwise resolve a reviewed catalog rule whose applicability and prerequisites are satisfied.
3. Apply current policy at all times: explicit user disable, known failures, impaired capabilities, incompatible model/API context, missing credentials, stale required state and pending uncertain commands take precedence over historical success. Review or invalidate bindings when operation semantics/revision or context changes.
4. Activate the eligible known HA control automatically using the historical unique ID. No need to send the control to establish that it is eligible. A route supported by catalog evidence is labeled `catalog_matched`, not physically verified on this VIN.
5. Where there is no eligible route, keep the status surface usable. Mark the control `unknown`, `ineligible`, `blocked` or `unavailable` with reason. Do not fabricate a value, silently fall back to V2, permanently disable a registry entry or require a manual test for ordinary use.
6. Save the binding and provenance. Re-evaluate after a meaningful vehicle/context/catalog change, fresh status evidence or reauthentication. Warm starts reuse validated bindings without repeating engineering discovery or unnecessary GETs. Do not automatically try an alternative mutation after a failed command.

Target performance: use the initial normal read pass and persisted bindings for the common supported path; no per-control network request solely to activate a control. Any extra read probes are bounded by a configured budget, quota and backoff. Exact time/GET budgets are acceptance measurements to establish across supported vehicle families, not a fabricated SLA. Fast discovery can be progressive while missing evidence is resolved.

## Evidence model and UX

Track separately: advertised capability, route applicability, valid mapped status, reviewed catalog match, local physical proof, current command execution result and freshness. Preserve explicit negative evidence and unknown outcomes. HTTP 207, 429, sleeping vehicles or auth/network errors do not establish unsupported status. Historical human approval does not override current security policy.

A normal end user sees standard HA entities and availability, plus concise reason/status diagnostics if something is unavailable. Workbench remains opt-in and administrator-only. A normal HA service or automation is an explicit configured invocation, not discovery; it must pass current eligibility, safety, cooldown and confirmation policy.

## Acceptance gates

- Supported new installation automatically creates applicable control entities without manual testing or Workbench interaction.
- Warm start restores valid bindings without extra per-command probes; changed route revision/context is revalidated.
- No mutating physical requests during setup, refresh, reload or fast discovery, including when evidence is absent; only allowlisted read-only GraphQL inventory POST.
- Exact-model/market/auth evidence is not applied to unrelated vehicles; disabled/failed/impaired cases fail closed.
- S-PIN controls require current credentials and policy; unknown lock status never means unlocked.
- Engineering manually tests one action at a time, persists prior to dispatch and handles restart/uncertainty; both modes use the same normal command lifecycle.
- Real-car acceptance separately validates the chosen routes for the supported vehicle contexts, including Q8, applicable MBB and rollback. CI and catalog matching do not prove physical operation.
