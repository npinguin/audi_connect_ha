# Audi Connect V3 — Community quick start and engineering how-to

**Use your Audi. Explore its capabilities. Build what's missing. Share what works.**

This guide is based on the experimental HACS release [3.0.0b12](https://github.com/npinguin/audi_connect_ha/releases/tag/3.0.0b12), not unreleased development changes. V2 remains the default and fallback. Compatibility varies by vehicle, model year, region, connected services and authentication. See [release notes](V3_RELEASE_NOTES_3.0.0b12.md) and [known gaps](V3_COMPLETENESS_AUDIT.md).

## Choose your path

| Audience | Goal |
| --- | --- |
| Everyday users | Connect your Audi and use native Home Assistant entities, without API knowledge |
| Explorers and testers | Discover missing or incorrect functions and share evidence |
| Engineers | Discover, configure, test and activate alternative API paths, then contribute reusable capabilities |

## 1. Everyday users — connect and use

1. Back up Home Assistant and note the installed Audi Connect version.
2. In HACS, add `https://github.com/npinguin/audi_connect_ha` as a custom repository (Integration). Select Audi Connect and explicitly install prerelease **3.0.0b12**. This replaces the same integration domain, not a second integration.
3. Restart Home Assistant. For a new installation, add Audi Connect under **Settings → Devices & services → Add integration**. For an existing installation, keep your config entry, vehicle devices and entity registry.
4. Sign in with myAudi if prompted. For Auth0, open the supplied login link, sign in, and copy the complete callback URL from your browser to the HA form. A localhost connection error after login is expected. Never share the callback URL.
5. Open **Audi Connect → Configure → Runtime → V3 — Experimental**, save and allow the integration to reload.
6. Open your Audi device page and use the available sensors and controls. No Engineering Dashboard or manual per-control test is required for normal use of eligible functions.

Depending on your vehicle, you can monitor battery, range, fuel, charging and access, view trips and maintenance information, or control climate and locking. Example automations include departure preconditioning, unlocked-car notifications and solar-surplus charging decisions using reported SoC. Verify the actual vehicle state before relying on remote commands. In b12, cabin climate uses one primary native Climate entity; charging and window heating retain explicit buttons pending reliable switch-state evidence.

**Rollback:** select V2 in Runtime options. Do not delete the registry. Downgrading the actual HACS package is separate; restore a compatible backup if needed. Full migration and rollback validation remain open.

## 2. Explorers and testers — discover what your Audi supports

1. Activate V3 as above. Open **Configure → Enable V3 Development Workbench** (administrator only).
2. Open **Audi Engineering Dashboard** in the HA sidebar and choose your car.
3. Start at **Overview**, then **Capabilities**. Select Access & security, Charging, Climate, Trips & location, Vehicle status, Service & maintenance or Remote actions. Browse **Data** and **Controls**; choose **All historical and local attributes** to find missing mappings.
4. Open **API evidence**. Select an applicable API family and run **Quick scan**. If useful, select **Full read-only scan / continue** to examine distinct reviewed GET routes, including unmapped jobs. Full scan is resumable, in batches of up to 12 calls with a quota reserve; it is not unrestricted endpoint discovery.
5. Review the HTTP outcome, schema, field inventory, missing mappings, capture timestamp and eligibility. Inspect the masked request/response from an existing execution without another API call. Detailed previews are bounded and session-only; do not repeat a physical action just to recover a preview.
6. Compare available information against myAudi and the actual car. Report incorrect values, stale captures, missing features or unexpected behavior with the contribution template below.

A sleeping vehicle, expired session, permission failure, missing field or rate limit is not proof of non-support. Record unknowns rather than guessing. Read-only discovery does not send wake or physical control commands. Never repeatedly scan to force a response.

## 3. Engineers — discover, configure, test, activate, contribute

Do not wait for a Python change to start exploring. The Engineering Dashboard is an opt-in local laboratory. A finding on your own vehicle can become a reviewed catalog rule for other compatible vehicles.

### A. Find new paths and possibilities

Start with the missing user capability, not an endpoint. Look at existing V3 catalog operations, legacy V2 mappings, the [Audi/VW Group API knowledgebase](research/cariad/README.md), open-source implementations and observations from your own authorized vehicle. Look for new response fields, alternative routes, model-specific differences and changes in API generations. Cross-brand research is a hypothesis, not proof a route works on Audi.

Use **API evidence** to inspect the operation matrix and response fields. Identify the correct value, type, unit, capture timestamp and context. For example, a reported electric range field may be a useful sensor; a Boolean oil warning must not become a numeric oil percentage.

### B. Configure and test read-only data

- In **Capabilities → Data**, select an existing attribute and open **Configure & test**.
- Choose an existing route, or expand **Advanced · define another API path and response mapping → Add custom read route**. Use the JSON template supplied by the dashboard. Define the supported relative CARIAD GET path and response extraction, with declared parameters and the correct semantic mapping. Never supply credentials, arbitrary hosts or auth headers.
- For a new local sensor, use **Add a vehicle-local sensor / capability group → Save local attribute**. Replace the illustrative JSON with an actually observed job and response paths; assign an appropriate type, unit and HA metadata.
- Select the candidate, use **Save candidate** to retain the draft, then **Test read-only GET**. Inspect the returned value, schema, capture time, units and errors. Compare it with the vehicle; test missing, stale, invalid and zero values.
- Use **Activate for polling** only when eligible and verified. Confirm that the entity is usable in HA and remains correct after a reload. A saved candidate is not an active sensor. Disable an invalid local mapping rather than invent a value.

Custom attribute/read-route support is limited in b12; not every response, method or transformation can be expressed. If blocked, capture the gap and propose a reviewed code-owned mapping/handler.

### C. Configure and test a vehicle control

Choose **Capabilities → Controls → Inspect & test** for a specific semantic action (e.g. climate on). Select an applicable catalog route or expand **Advanced · Add an alternative command template**. Configure a trusted family, relative path, method and supported typed parameters/body using the supplied JSON template. Use **Save alternative route · no command sent**. The engine owns the host, authentication and allowed substitutions. Never paste a real S-PIN or token into a template; protected operations require the account's securely configured S-PIN and current eligibility.

1. Verify prerequisites and make sure the car is safely parked and the action is safe. Select exactly one vehicle, route and action. Provide required parameters; review the request.
2. Check the exact-action approval checkbox and select **Send one test command**.
3. Inspect HTTP acceptance, backend result and fresh telemetry/readback separately. Physically check the car where necessary.
4. Record **Verified working**, **Did not work** or **Not sure**. Do not retry blindly or try an alternative mutation after an uncertain result; inspect the car and resolve the pending outcome first.
5. Only if the route is runtime-ready and verified, select **Activate verified route**. Use its native HA control, verify readback, and test safe restart/reload behavior. Disable the control if the evidence is inadequate.

Some custom parameterized command activations and custom PUT templates are incomplete in b12. A successful test does not guarantee activation. Never bypass safety, permission, cooldown or API quota restrictions. Discovery itself never actuates the car.

### D. Turn your experiment into community value

Use the verified route locally where supported. Then report or propose a reusable capability: vehicle applicability, relative operation, response mapping, semantic meaning, prerequisites, exclusions, test evidence and regression cases. A successful Q8 experiment is not proof for every Audi.

Open a [fork issue](https://github.com/npinguin/audi_connect_ha/issues) or a focused pull request; coordinate upstream contributions via [Audi Connect](https://github.com/audiconnect/audi_connect_ha). Contributors can start from an evidence report without writing Python. Maintainers review evidence, normalize the catalog definition, validate security and applicability, add regression tests and test other vehicle contexts. Promote only reviewed definitions into automatic end-user discovery. Never require every future user to repeat the original engineering experiment.

## Contribution template (copy into an issue or PR)

- Integration version / runtime / HA version:
- Vehicle model, model year, ICE/PHEV/BEV, region and API/auth family:
- User value / missing or incorrect capability:
- Attribute or semantic action / proposed HA entity type, unit, data type:
- Sanitized relative route, method, required parameters and response structure:
- Expected and observed outcome; HTTP, schema, capture freshness, readback and physical verification (worked/failed/uncertain) separately:
- Which vehicle contexts were tested, prerequisites, limitations and negative evidence:
- Local activation and restart result (if applicable):
- Proposed reusable mapping/rule, regression test or next step:

Review/redact even masked evidence before sharing. No VINs, credentials, callback URLs, tokens, S-PINs, request IDs, private trip or location data, or raw personal payloads. The dashboard is not a public export tool. Automatic contribution export/import is a proposed enhancement, not a b12 feature.

## Current boundaries and further reading

- V3 is experimental; not all V2 functions are migrated or physically validated across model families.
- Normal users should not need the engineering workbench; reviewed eligible routes are the intended automatic path. Unsupported or inconclusive functions remain unavailable with reasons.
- HTTP acceptance is not physical completion; catalog matching is not local vehicle verification. Use Audi services responsibly; respect rate limits, authorization and the vehicle's safety restrictions.
- [Configuration and dashboard](V3_CONFIGURATION.md) · [Development profiles](V3_DEVELOPMENT_PROFILES.md) · [Fast discovery policy](V3_ADR_002_FAST_DISCOVERY.md) · [Architecture](V3_ARCHITECTURE.md) · [Test matrix](V3_TEST_MATRIX.md).
