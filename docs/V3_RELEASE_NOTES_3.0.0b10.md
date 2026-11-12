# Audi Connect 3.0.0b10 — product entity rationalisation

Experimental HACS test only, subject to exact-SHA CI. Not stable or physical acceptance.

- Audi Engineering Dashboard: separate overview, capabilities, single-function testing and API evidence; corrected capability-scoped controls and selection safety.
- Vehicle doors/windows, oil warning, parking lights and movement are normal sensors, not diagnostics. Consistent automotive door icons and HA-native window state icons; custom mirrored automotive icon family remains open.
- Native climate is primary. Existing quick switch and raw climate state remain compatible but hidden by default. Unknown climate and plug enums fail closed.
- Canonical battery and total range can use timestamp-aware alternative sources. Fuel uses explicit fuel percentage, not inferred engine SOC. Engine ranges receive role-aware names where known; duplicate percentages hidden only with evidence.
- Existing registry entries remain intact; compatibility hiding is reversible and tracked, as are category changes. Charging settings use CONFIG and require supported options/read/write capability.
- Diagnostics expose actual category, original icon and hidden status. No new physical commands or extra cloud calls.

## Acceptance
Back up HA, install b10, restart. Verify existing device identity, normal sensor categories, climate primary control, compatibility visibility, oil warning, charging setting eligibility, range and SoC, dashboard navigation, registry/automation history and V2 fallback. Check both new and upgraded entries. Export fresh diagnostics. User overrides are not forcibly overwritten. Known unavailable historical entities and unknown button IDs remain for investigation rather than destructive cleanup.

Open: complete custom icon family, model identity, all unavailable registry entries, full capability-level freshness and schema coverage, physical Q8 and ICE/BEV acceptance. Stable gates remain closed.
