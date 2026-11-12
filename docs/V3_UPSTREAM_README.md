# Proposed upstream README section — Audi Connect V3

Maintainer proposal, documentation only. Copy the section below into the upstream README under Description or Community/Development, subject to upstream review. It intentionally identifies V3 as experimental and links to the fork rather than implying the official HACS release already contains V3. Replace fork links with upstream-relative links only when the corresponding implementation and documentation are accepted.

---

## Audi Connect V3 — community-powered innovation

**Configure → Discover automatically → Use.**

Building on the excellent work of the original Audi Connect maintainers, V3 explores a new generation of Audi integration for Home Assistant: discover what each car supports, use native HA entities, and make it easier for the community to add missing capabilities across vehicle and API generations.

| For | What V3 offers |
| --- | --- |
| Everyday users | Connect myAudi once, automatically discover available functions and build automations with native HA sensors and controls. No API knowledge required for eligible known capabilities. |
| Explorers and testers | Inspect capability coverage and read-only API evidence, compare results with your car and report missing or incorrect functions. |
| Engineers | Validate the same end-user journey, selectively discover and edit failed APIs, test and activate verified functionality where supported, and share reusable evidence. Many experiments need no Python changes. |

**Use your Audi. Explore its capabilities. Build what's missing. Share what works.**

A successful experiment becomes valuable to the wider community when its route, mapping, applicability and validation evidence are reviewed and incorporated into the shared catalog. The aim is for compatible vehicles to benefit automatically, without requiring each owner to repeat the research.

**Current status:** V3 is an experimental fork prerelease, not a feature of the official stable upstream release. V2 remains the default/fallback in the fork. Full parity, cross-model physical validation and rollback acceptance remain open. No automatic physical actions during unattended discovery; optional guided physical verification requires individual consent; API availability varies by car.

- [Experimental V3 release (3.0.0b19)](https://github.com/npinguin/audi_connect_ha/releases/tag/3.0.0b19)
- [How-to: users, testers and engineers](https://github.com/npinguin/audi_connect_ha/blob/feature/v3-clean-discovery/docs/V3_COMMUNITY_HOWTO.md)
- [Product vision, architecture and delivery roadmap](https://github.com/npinguin/audi_connect_ha/blob/feature/v3-clean-discovery/docs/V3_ARCHITECTURE.md)
- [API knowledgebase](https://github.com/npinguin/audi_connect_ha/tree/feature/v3-clean-discovery/docs/research/cariad)
- [Community diagnostics and privacy](https://github.com/npinguin/audi_connect_ha/blob/feature/v3-clean-discovery/docs/V3_COMMUNITY_DIAGNOSTICS.md)
- [Share a discovery or report a gap](https://github.com/npinguin/audi_connect_ha/issues)

Use a Home Assistant backup and opt into the beta only if comfortable with experimental software. Respect Audi service limits, protect personal data and verify physical results before relying on remote controls.
