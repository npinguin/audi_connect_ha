# Audi Connect 3.0.0b30 — lock and Workbench stabilization

Experimental fork prerelease. V2 remains default and fallback; V3 is opt-in. Not a stable upstream release.

- Distinguish known HTTP acceptance from genuinely uncertain transport. Bound the normal lock/unlock transition using the existing 30-second cooldown; a subsequent explicit authorized action is allowed after cooldown when acceptance is known. Never replay a command or fabricate a physical locked/unlocked state.
- Expire the native lock transition with a one-shot local state update, without additional Audi requests. Preserve S-PIN, route and genuine uncertainty guards.
- Keep engineering Test buttons visible when blocked, explain the pending action, and distinguish route validation from current command outcomes. Explicit physical review is still required for engineering experiments.
- Export sanitized pending engineering and unresolved normal command context in diagnostics. Preserve B29 common entity metadata.
- PR #33 passed 1,139 Python tests, Workbench interaction tests, lint and Validate. No new entities or extra API calls.

The preceding published B29 source is already offered in upstream PR #918. B30 does not automatically update the upstream review branch. Exact-package HACS gates must pass before publication.

Open: repeated real-vehicle lock/unlock acceptance, including after extended runtime, engineering review UX, and full alignment of route availability with immediate dispatch eligibility (including cooldown). Stable V3 acceptance remains NO GO.
