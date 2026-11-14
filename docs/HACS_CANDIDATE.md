# Audi Connect 3.0.0b34 — experimental audit and multi-source acceptance

Experimental fork HACS prerelease for live acceptance, not stable and not an upstream release. V2 remains the default; V3 is opt-in and EU Data Act is disabled by default.

## Changes since B33

- Repair generated Auth0 account titles and reject reauthentication of a different account. Preserve config entry, device and entity identities.
- Native HA entity presentation from the existing product contract, with English, German, Dutch and French names and registry rollback protection.
- Select the newest valid equivalent observation across channels; native command evidence remains independent of display selection.
- Use the existing optional Data Act channel, not a fallback. Acknowledge deliveries after processing, distinguish delivery and authorization states, and publish relevant status changes.
- First 20 exact dataset field mappings for 19 canonical attributes based on the Q8 review. Generic discovery inventories safe field identities, including unmapped fields, through the existing schema inventory and Workbench. No raw values, automatic entity generation or commands.
- Enrich missing manufacturer model or year from explicit, same-VIN consented portal metadata when available. Never promote a nickname or infer model from VIN. Actual Q8 metadata availability is not yet proven.
- Bound trip retry, separate health observations from reporting, protect setup/unload and keep native outage handling independent of the optional channel.
- Consolidate ownership, presentation, observation selection and rollback; no new runtime module, entity, polling task, native request route or persistent store.

Exact merged PR #48 head passed 1,226 Python and 39 Workbench tests, lint/pre-commit, HACS and hassfest. The candidate workflow validates HA 2026.7.0 and 2026.11.1 and the archive checksum. B33 product source has been offered through the existing upstream PR #918.

## Live acceptance

Back up HA and install this experimental beta without deleting existing entities. Select V3 if needed. For optional Data Act, first verify an existing authorized continuous portal request; enable the channel in integration options, enter portal credentials locally when needed, then inspect Integration status and Model. The optional Workbench shows observed fields, mappings and gaps. Verify real delivery, manufacturer identity provenance, source freshness, disable/restart, and native behavior during a portal outage.

Q8 Data Act sign-in, real dataset content, manufacturer model/year, Q5 localized names and rollback, physical charging/climate controls and representative model acceptance remain open. Do not share credentials, VIN, coordinates or raw payloads. This is not stable acceptance; audit issue #44 remains open.

Source: merged PR #48, 10255ae45f84380cd587ad1becffe31871dfba35.
