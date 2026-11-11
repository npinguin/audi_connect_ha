# Audi Connect V3 — Release acceptance and future expansion

## Beta packaging gates vs real-vehicle acceptance

| Gate | Evidence required | State before release |
|---|---|---|
| Code / catalog | Valid JSON + schema references, no arbitrary hosts/methods or duplicate operation IDs | Synthetic tests exist; full CI on release SHA required |
| Pytest | All repo tests pass on exact head SHA | Pending fresh CI |
| Hassfest | Home Assistant integration manifest, translations, entities and dependencies validate | Pending fresh CI |
| HACS | HACS action passes in fork with GitHub Issues enabled | Pending setting + CI |
| In-place reconfigure | V2→V3→V2 on same HA entry, no extra login, no lost unique IDs | Requires real HA |
| One poller | One interval and no additional scheduled GET / auto wake | Code design; measure live |
| Q8 ON/OFF | One explicit start/stop each with real physical/cloud state evidence | Requires live vehicle |
| Context security | Q8 route only with Audi-sourced model metadata, not nickname; no use of legacy token for Auth0 | Synthetic tests in PR |
| Unknown support | Opt-in allowed only for unknown; explicit unsupported or impaired still blocked | Synthetic tests in PR |
| Staleness / errors | Unknown remains unknown; no HTTP 2xx treated as physical success; 429/5xx do not delete entities | Synthetic tests + live |
| Privacy | No VIN/token/raw payload in diagnostics and logs | Synthetic tests + audit required |
| Rollback | Existing climate ID and historical entity registry persist | Needs real HA |

## Test scenarios

- Auth0 Q8 PHEV: report climate supported, start without temperature body, stop, check actual state and no duplicated quick switch.
- Auth0 non-Q8: no implicit Q8 bodyless command; if temperature unknown, reject settings variant before request.
- Auth0 without advertised capabilities: read-only status still possible; control disabled until explicit experimental opt-in. Explicit negative remains rejected.
- Mixed legacy + Auth0 in one account: legacy vehicle stays on V2 climate, authentication and route context never cross.
- Intermittent 207/partial responses: retain last known fields without claiming freshness, no phantom unsupported.
- Rate limited / sleeping / offline: no automatic wake or aggressive retries.
- No temperature support: V3 climate works as ON/OFF without presenting a writable target slider.
- Existing automation using old climate unique ID: preserved; old quick-switch automation must be migrated first.
- Options edits: dealer metadata, local settings, API token rotation do not lose runtime mode.
- Two vehicles: independent route evidence, never export an identifiable VIN.

## Future V3 capability expansion order

**First:** prove climate end-to-end and close owner boundaries. **Then:** implement a safe in-HA Development GET Workbench to edit validated relative API path templates and extract response fields; separately capture HTTP success, schema correctness, freshness and capability observations. **Next:** introduce automatic GET path selection based on context-local and per-route evidence and documented cooldown. **Then:** controlled optional community compatibility reporting (explicit opt-in, aggregated, privacy reviewed). **Later:** migrate charging, trips, health and wake one capability at a time. Control POST/PUT experiments require a separate explicit risk boundary; they must never inherit GET auto-fallback behavior.

The beta does **not** claim those later capabilities or a generalized live templating UI exists. Every new capability requires an exact owner, contract tests, backward-compatibility check and rollback path before activation.


**Migration guard:** verify a V3-mode reload skips the legacy orphan-device
cleanup entirely, and an empty initial V2 inventory never removes registered
HA devices. A missing initial vehicle scan is **not** a delete signal.


## Phase separation (prevents release-test deadlock)

To publish an **experimental HACS prerelease for user testing**, first pass
pytest, hassfest, HACS validation, source/manifest-version checks and privacy
review on the exact head SHA. Enable fork Issues before the HACS check.
The actual V2→V3→V2 Home Assistant smoke test, Q8 real vehicle ON/OFF,
physical confirmation, battery/API rate observations and automation review
are **post-prerelease beta acceptance**, required before calling V3
production-ready, merging or recommending it as stable. Do not claim those
were validated simply because the prerelease tag exists.
