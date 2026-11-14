# Audi Connect 3.0.0b38 — field-test correction candidate

Experimental HACS prerelease. V2 remains the default and rollback, V3 opt-in, Data Act disabled by default. Not an accepted stable release.

## Changes since B37

- Source discovery and coverage visible per API family, including actual normalized scalar values, alternative sources, capture/receipt/delivery, source paths and coarse authentication context. No raw dataset or credentials in exported diagnostics.
- All 84 observed Data Act UUID/name pairs have explicit mapping destinations: 35 existing canonical attribute mappings and 49 bounded read-only details. Mapping coverage is not physical support or 84 valid measurements. No new entity IDs or command routes.
- Dedicated localized HA source form with connect/reconnect/disconnect and validation before replacing working credentials; remove blank menu and empty confirmation.
- Declarative model/year field paths and retained identity provenance; preserve source withdrawal, native account, registry and trip history. Real OEM metadata is still missing from the observed Data Act consent response. Do not substitute nickname or infer from VIN.
- Q5 field evidence: 1,000 persistent trips, physical charge start/stop on B35, German translations improved, numeric quota. V2 opt-in remains intentional. Existing HACS master/beta behavior remains upstream review concern.
- No new host, web authentication method, scheduler or country-specific core branch. Future myAudi web inventory requires a reviewed, authorized source contract.
- Exact PR #53 passed 1,241 Python regression tests and lint/Validate. Candidate workflow verifies both HA compatibility versions and archive.

## Acceptance

Back up Home Assistant. Upgrade over B37 without deleting the integration or devices. Restart, retain V3 and Data Act credentials. Inspect Workbench per-family coverage and values, verify the source options form, reconnect with correct credentials and test failure recovery separately if desired. Check new capture after driving and active charging; preserve entity IDs and trip history. Model, model year and OEM drivetrain remain explicit acceptance blockers. Confirm actual source field evidence before adding another identity route or release. No stable promotion or declaration of full normalization/live coverage. Issue #44 remains stable gate.

Source: merged PR #53, 8436733652dda108b851d8934ca03e2a7934f121.
