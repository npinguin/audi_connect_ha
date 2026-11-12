# Branch governance — consolidated V3 development

- `master`: upstream mirror, never develop here.
- `main`: integrated source baseline; a merge is not a release or production acceptance.
- `feature/v3-clean-discovery`: sole internal development stream; short-lived fixes return here. No parallel persistent development branches.
- `contrib/upstream-audi-connect-fixes`: external contribution only, preserve while upstream PR #915 is open; never use as the V3 development base again.
- `research/cariad-cross-brand-api-2026-11-11`: external research contribution only, preserve while upstream PR #916 is open; never use as the V3 development base.

## Consolidation decision (2026-11-12)

Latest V3 source cc3ec59d2faf839b74fabe48f16f48fb96e83021 is authoritative. Preserve all branch commit histories; do not reintroduce superseded V3 pilots, V2 probe services, old ZIP artifacts, or old automatic fork release workflows from other branches. Retain upstream-oriented V2 baseline and explicitly restore four stable V2 reliability fixes (cancellation, GPS retry, command confirmation, numeric statistics) with their regression tests from 43be48268262ef9e2c8942a955888415b8e86dc8. Research documents retained. V3 implementation and its release gate unchanged. Do not publish 3.0.0b8 until the code-complete gate is explicitly passed; stable promotion also needs physical vehicle and HA rollback proof.

Historic branch heads remain reachable through the consolidation commit. Branch closure is not a claim of feature parity; all outstanding parity and architecture work stays on the canonical development branch.

## Architecture closure

The seven obsolete internal branches were removed after ancestry and active-PR checks. The two upstream contribution branches remain protected. All closure work follows [V3 Architecture Closure](V3_ARCHITECTURE_CLOSURE.md) and [ADR 002](V3_ADR_002_FAST_DISCOVERY.md) on the canonical development branch. A design/documentation commit is not implementation acceptance or release authorization.

## Explicit experimental HACS test exception — 3.0.0b8 (2026-11-12)

The maintainer requested an installable test prerelease before static parity sign-off. The one-time exception is limited to the exact b8 release-intent commit on the canonical development branch, after full CI. See `governance/B8_EXPERIMENTAL_TEST_RELEASE.json`. Do not alter parity flags, publish as latest, replace existing tags, change `main`, or reuse this exception. Normal code-complete and stable gates remain unchanged.
