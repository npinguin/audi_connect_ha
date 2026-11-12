# Audi Connect 3.0.0b4 — V3 Climate reference stabilization

**Experimental HACS prerelease.** V2 and V3 remain together in one package
and Home Assistant config entry, with only one active runtime. V2 is default.

## Fixed since b3
- A Climate value without its own valid vehicle capture timestamp never
  inherits the prior value's freshness.
- Stale GET responses may try a distinct read-only candidate within quota.
- Later-discovered vehicles restore saved API candidates and evidence.
- JavaScript Workbench save/rerender regression added to CI.
- V3 independent architecture, install and next-engineer docs aligned.
- Release includes SHA256 checksum for the HA install ZIP.

## Retained baseline
Save candidate is independent from Activate verified route. Workbench only
appears with V3 and explicit administrator opt-in. Capability Status shows
API family, relative route, and verified/untested/V2-reference evidence.

## Not yet proven
Physical Q8 testing, exact live timestamps, climate Start/Stop readback,
actual HA startup and V2→V3→V2 entity/automation rollback. Only Climate and
cloud/core capabilities are independently implemented in V3.

## Next engineer
Expand read-only capability/attribute discovery based on V2 jobs and newly
researched paths. Preserve route, family, mapping, timestamp and test evidence,
without hardcoding per-car API forks or claiming untested routes work.
