# Upstream reconciliation — b13 baseline

Upstream target for review is **dev**, not master: #915 and #916 are merged in dev (not master). The current official master is 2.5.2. Do not resubmit those contributions as new. Exact snapshot: [upstream master](https://github.com/audiconnect/audi_connect_ha/commit/d12f74c35c1c961f3b040e5cc77acbca2a5cca26), [upstream dev](https://github.com/audiconnect/audi_connect_ha/commit/c4f095dd46a3b5c7b438633ac2db16aabffe8f28), [published b13](https://github.com/npinguin/audi_connect_ha/commit/9bd8d77b066a3c8ece1a6f4ebdcb8f31242f7300). The [machine-readable blob inventory](V3_UPSTREAM_RECONCILIATION.json) covers every shared production file, excluding the new V3 package. This is not proof of semantic equivalence.

| Classification | Count | Review |
|---|---:|---|
| Identical to upstream dev | 17 | No new shared-file change to submit |
| Diverged on both sides | 17 | Review dev-to-fork delta, preserve upstream behavior unless documented |
| Fork-only delta | 5 | Review necessity for native V3, separate packaging changes |
| Upstream-only | 1 | api_probe.py: explicitly reconcile retired probe with upstream public services and replacement |

## Review strategy

- Existing upstream PRs: [#915](https://github.com/audiconnect/audi_connect_ha/pull/915) Auth0/control/reliability and [#916](https://github.com/audiconnect/audi_connect_ha/pull/916) API knowledgebase. Already merged; only incremental changes belong in a new PR.
- Review the 17 divergent files for semantic behavior, not merely byte identity. Prioritize shared auth/transport/services, config/diagnostics, native platform routing and service contracts, then translations.
- Keep legacy public probe compatibility explicit: upstream dev contains api_probe.py, b13 deliberately retired the old probe runtime/services. Decide with maintainers whether to retain a V2 compatibility adapter or document migration; do not silently remove a public contract.
- Separate fork-specific release workflow, manifest URLs and beta governance from the upstream product proposal. Do not submit fork release authorization as upstream authorization.
- The internal draft PR #22 is the integration review. Do not merge or create a competing release branch before compatibility/evidence review. Upstream dev PR scope must be agreed with maintainers.

The existing V2 delta register remains pinned to master and continues to enforce shared source drift. This second comparison is a frozen review artifact against the merged upstream dev baseline; refresh it when preparing the actual upstream PR.
