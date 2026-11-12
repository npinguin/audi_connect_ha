---
name: Bug report
about: Report a reproducible Audi Connect integration issue
title: ""
labels: ""
assignees: ""
---

**Problem and expected behavior**
What happened? What should happen? Is this a regression from a specific version?

**Environment**
- Audi Connect version and mode (V2 or V3):
- Home Assistant version:
- Vehicle model/year/powertrain (no VIN):
- Region:
- Does the same function work in myAudi under the same conditions?

**Reproduction**
Steps, relevant vehicle prerequisites, and approximate time of failure.
For commands, distinguish backend acceptance from observed physical effect.
Do not repeat an uncertain remote command just to reproduce an issue.

**Diagnostics**
Download native integration diagnostics from Settings > Devices & services > Audi Connect > three-dot menu > Download diagnostics. Do not attach the original file: Home Assistant may add unrelated integrations, installation metadata and identifiers. Share only the reviewed Audi Connect `data` object and HA/integration versions. Remove response previews from older releases. See [diagnostics privacy](https://github.com/npinguin/audi_connect_ha/blob/feature/v3-clean-discovery/docs/V3_COMMUNITY_DIAGNOSTICS.md).

Never attach tokens, credentials, S-PIN, VIN, coordinates, raw HTTP payloads, private trip history or the internal profile store. Logs/screenshots are optional; redact identifiers before sharing.
