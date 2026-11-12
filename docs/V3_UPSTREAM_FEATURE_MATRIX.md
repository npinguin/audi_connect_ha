# V3 upstream feature and evidence matrix

This review artifact complements the [canonical product inventory](../custom_components/audiconnect/v3/product_entities.json) and [operation catalog](../custom_components/audiconnect/v3/full_catalog.json). The [machine-readable matrix](V3_UPSTREAM_FEATURE_MATRIX.json) inventories **140 product identities (31 V3 extensions), 62 reviewed catalog operations, 20 control aspects and 103 b12 observed field records**. Counts are static contracts, not enabled entities or supported features on a particular car.

| Capability | Candidate improvement | b12 physical evidence / outstanding |
|---|---|---|
| Climate | Native climate, request/readback separation, window heating, timers | Stored start/stop worked on b12; b13 physical validation open |
| Charging | Native switch, explicit setting eligibility, profiles, care and departure timers | No b13 physical acceptance; fresh charging data required |
| Access | Lock, partial component handling, named doors/windows and lights | Unlock HTTP acceptance on b12, not physical proof |
| Vehicle status | Identity, engine role, range/SOC/fuel, boolean oil, services, discovery | OEM label and oil polarity need live confirmation |
| Service | Inspection, warnings/campaigns, battery support and readiness | Fresh real warning/12V schema required |
| Mobility | Modern trip metrics and durable archive, read routes | b12 trip GET evidence; full endpoint/history coverage unknown |
| Remote | Wake-aware cooldown, guarded explicit actions, coverage | b12 wake HTTP 204 not proof of wake; b13 not validated |

The eight previously open observed fields now have an explicit code disposition (including the invalid timeInCar sentinel). The original b12 evidence file remains unchanged and truncated; this is not a claim that all OEM fields are known. B13 release CI passed 943 Python tests plus frontend/HACS/hassfest; fixture review files are capability-level links, not an assertion that every operation was individually exercised. Post-b13 code is unshipped. Vehicle-specific readback, physical success, model coverage and rollback are still separate evidence gates.

To complete the matrix, consume fresh sanitized diagnostics per vehicle context and report operation, schema, capture freshness, HA projection, physical outcome and candidate version separately. Do not transfer prior b12 results to b13.
