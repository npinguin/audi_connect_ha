# Audi Connect 3.0.0b35 — experimental capture stability

Experimental fork HACS prerelease for live acceptance. V2 remains the default and fallback, V3 is opt-in, and EU Data Act remains disabled by default. Not a stable or upstream release.

## Changes since B34

- Reuse the existing Status capture validity policy for observation acceptance, family cache reconciliation and alias selection.
- An implausible future vehicle timestamp can no longer replace a valid timestamped observation or prevent recovery with a valid capture. Unknown timestamps remain unknown, not fresh measurements.
- Keep the change within one existing runtime file, with two focused regression tests. No new modules, state owners, commands, entities, requests, polling tasks or configuration.

PR #49 exact head passed 1,228 Python tests, Workbench, pre-commit, HACS and hassfest. The merged dev tree is identical to that tested head. B34 product source is offered through existing upstream PR #918. The candidate workflow validates both supported HA versions and archive integrity before publication.

## Live acceptance

Back up HA, retain the existing config entry and entity registry, and test V3 with the same Q8/Q5 scope as B34. Verify capture freshness and recovery, Data Act authorization and delivery if enabled, native charging and climate physical readback, restart and V2 rollback. Stable release remains NO GO; issue #44 remains open.

Source: merged PR #49, 37e81fe1399d85c35c3740189318c58eeb3584d2.
