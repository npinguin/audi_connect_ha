# Audi Connect 3.0.0b45 — community stabilisation beta

Experimental HACS test release. V2 remains the default and fallback; V3 is opt-in. This is a stability release, not a stable promotion.

## Changes since B44

- Separate observed native VCF allowance from local request accounting. Ordinary read requests no longer debit an assumed remote command budget.
- Keep server rate-limit recovery scoped to the observed API family and request class without claiming independent OEM quotas; retain separate native and EU Data Act checkpoints.
- Preserve the existing trip refresh cadence across Home Assistant restarts: three hours after a completed cycle, fifteen minutes after an incomplete cycle. Context changes permit a new refresh.
- Retain B44 startup recovery, existing controls, entity identifiers and trip history. No new API routes, scheduler or storage layer.

## Community acceptance

Back up Home Assistant before installing. Upgrade the existing integration without deleting the device or config entry; restart HA. Confirm startup, existing entities and historical data, native status, trip refresh and control availability. Test supported controls individually. For charging START/STOP, verify actual charging power and vehicle status independently; an accepted request or matching later status is not proof of execution. Do not rely on unconfirmed command state for unattended energy automation.

Please report model/year, region, HA and integration versions, steps, expected versus observed behavior, relevant timestamps and sanitized integration diagnostics. Review diagnostics before sharing; do not include credentials, VINs, tokens or other private information.

## Validation and remaining risks

Source: merged PR #74, a6fbf6f3f835b77b69e414696d43686131aff652; includes native API correction PR #73. Exact-head e51af7f56c850b354d3450d9240e0b6138ee5416: Test #2214 and Validate #2215 passed (1,335 Python tests, HA 2026.11.1). The existing publication workflow additionally validates the exact package, Workbench, hassfest, HACS and checksum before publication. Physical cross-model acceptance, charging command confirmation, Data Act freshness and broader adaptive polling remain open. Stable gate #44 stays open. Upstream PR #918 remains on the preceding B44 product source at the time of preparation; the existing one-beta lag gate is retained. No stable or upstream merge implied.
