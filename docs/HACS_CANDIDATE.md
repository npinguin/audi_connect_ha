# Audi Connect 3.0.0b27 — native evidence beta

Experimental fork prerelease; V2 remains default and fallback. Not a stable upstream release.

- Consolidated charge-mode normalization: capture provenance, explicit empty options, invalid values and stale replay. No relaxation of write eligibility.
- Native trip coverage follows existing snapshots, and missing entity reasons reuse source and command evidence.
- Existing b26 timer, ETA and schema evidence fixes retained.
- Publication requires the previous published beta's pinned product code, tests and documentation to be included in the upstream delivery branch. No automatic upstream push; release-only metadata stays in the fork.

Source PR #29 passed Test and Validate. The identical source snapshot is already offered in upstream PR #918. Exact-package CI on both Home Assistant versions is required before publication.

Physical Q8 command verification, vehicle identity, remaining capability/entity reconciliation and V2 parity remain open. No new vehicle API requests, routes or runtime layers.
