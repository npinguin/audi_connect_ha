# Audi Connect 3.0.0b23 — corrective closure

Experimental fork prerelease for Home Assistant acceptance. Source: PR #24 at 22911d86a567681758aa1be7540fac561bf988a4. V2 remains the default and fallback.

- Centralized advertised charge-mode validation for normal commands and HA select.
- Serialized registry migrations and ignored stale runtime notifications.
- Refused known numeric credential literals in portable definitions; shared backend/frontend import fixture.
- Encapsulated discovery state, consolidated typed climate settings and reviewed read paths.
- Aligned minimum Home Assistant version with the tested 2026.7.0 baseline.

No new vehicle operations. Physical verification, full feature parity, remaining engine cleanup and end-to-end acceptance remain open. Back up HA and validate real vehicle outcomes before relying on controls. This is not a stable release.

The existing packaging gate verifies exact runtime equivalence except the manifest version, both HA regression suites, frontend, lint, HACS, hassfest, checksum and merged PR #24 at its pinned head.
