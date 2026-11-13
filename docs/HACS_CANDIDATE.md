# Audi Connect 3.0.0b25 — clean integration beta

Experimental fork prerelease; V2 remains default and fallback. Not a stable upstream release.

- Includes b23 charge-mode corrections and b24 climate continuity, preserving validated last-known climate state through restart without treating it as fresh telemetry.
- Workbench cache key follows the packaged script, not a hardcoded beta version.
- Charging completion time follows valid source duration and is invalidated by newer invalid observations; older cached data cannot overwrite the newer evidence.
- Existing documentation links ownership, source inventories and remaining acceptance gates.

The integrated source PR #27 passed Test and Validate (1,120 Python tests). The candidate additionally requires exact-package CI on the minimum and current tested Home Assistant versions, frontend checks, pre-commit, Hassfest and HACS validation.

Physical Q8 climate and charging readback, missing vehicle identity, capability/entity reconciliation, representative ICE/PHEV/BEV validation and V2 parity remain open. Do not interpret HTTP success as physical execution. No new vehicle API requests or command routes.
