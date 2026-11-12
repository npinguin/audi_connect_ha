# Engineering Documentation

The upstream [Audi Connect README](../readme.md) remains the authoritative user guide for installation, configuration and vehicle controls.

## Community and onboarding

- [V3 community quick start and engineering how-to](V3_COMMUNITY_HOWTO.md) — user, explorer and engineer workflows, with contribution template.
- [Proposed upstream README section](V3_UPSTREAM_README.md) — copy-ready community positioning and experimental release disclosure.

## V3 engineering — authoritative current design

- [Architecture and module ownership](V3_ARCHITECTURE.md) — current baseline versus approved target.
- [Implementation progress](V3_CLOSURE_IMPLEMENTATION.md) — actual completed changes and remaining closure gates.
- [Architecture Closure plan](V3_ARCHITECTURE_CLOSURE.md) — migration ownership, work packages, quality gates and definition of done.
- [ADR 002: engineering discovery and end-user fast discovery](V3_ADR_002_FAST_DISCOVERY.md) — automatic control recognition/activation without automatic physical testing.
- [Configuration](V3_CONFIGURATION.md), [development profiles](V3_DEVELOPMENT_PROFILES.md), [HA identity contract](V3_SHARED_ACCOUNT_AND_HA_ENTITY_CONTRACT.md), [test matrix](V3_TEST_MATRIX.md), [parity baseline](V2_V3_PARITY_BASELINE.json), [branch governance](BRANCH_GOVERNANCE.md).
- [b9 release notes](V3_RELEASE_NOTES_3.0.0b9.md) — authorized experimental HACS test; stable gate remains closed.
- [b8 release notes](V3_RELEASE_NOTES_3.0.0b8.md) — historical experimental release.

## Research

- **[VW Group / CARIAD API research](research/cariad/README.md)** — canonical English research knowledge base, including the VW Group API evolution, cross-brand endpoint atlas, Audi/VW/Škoda/CUPRA/Porsche overlap, read-only and delayed EU Data Act feed, parked-vehicle data freshness, authentication/capabilities an adaptive multi-generation auth/API/vehicle/capability target architecture, NFR requirements, early experimental feature delivery and an engineering playbook.

This documentation is **research**, not an active deployment or a manufacturer-endorsed API contract. Do not assume unverified cross-brand endpoints work for Audi.

- [b10 release notes](V3_RELEASE_NOTES_3.0.0b10.md) — authorized experimental HACS test; stable gate remains closed.

- [b11 release notes](V3_RELEASE_NOTES_3.0.0b11.md) — experimental HACS test, exact-SHA validation required.

- [b12 release notes](V3_RELEASE_NOTES_3.0.0b12.md) — experimental HACS test, exact-SHA validation required.

- [V3 completeness audit](V3_COMPLETENESS_AUDIT.md) — pre-next-HACS gate and sanitized b12 capability evidence.
