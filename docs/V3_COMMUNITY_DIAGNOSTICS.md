# Community diagnostics and release acceptance

Native V3 diagnostics schema 2 is a local, read-only structural report. It retains operation outcomes, health, identity/auth role metadata, per-job schema and truncation, canonical attribute dispositions, discovery disposition, entity projection and stored physical evidence. Historical schema fields are a delta: combine the current structural inventory with historical-only rows to reconstruct the observed union; historical rows do not imply current support. API response previews remain restricted to the admin Workbench; they are not exported. Do not publish internal profile stores or raw logs. HA wraps the report with environment metadata. **Do not attach the complete Home Assistant download to a public issue.** Retain only the integration-specific `data` object and the Home Assistant and Audi Connect versions. Exclude installed integration inventory, system details, setup times, issues and config-entry identifiers. Inspect the result; remove response previews from older releases. Redact identifying custom names and unnecessary exact event times.

Reference testing found vehicle-specific charging-write limitations in both runtimes. Do not force unsupported writes or generalize to other vehicles.

Open gates: identity recovery, complete schema/attribute disposition, target HA matrix, live and rollback acceptance, static parity and upstream reconciliation. Do not claim stable readiness from diagnostics or CI alone.

Simplification rule: use the existing evidence, capability, command and storage owners. Remove duplicate paths, representations and writes; new policy needs a specific measurable reason and regression coverage.


The public export is a structural projection, not a dump of the private profile. On the b18 Q8 snapshot, removing previews and duplicate historical rows reduces the serialized export from 359323 to approximately 263815 bytes before adding attribute statuses. Do not treat this simulated reduction as a live b19 result. The remaining quota is a conservative estimate when a response omits the quota header. Stored control evidence is not an exact-release physical acceptance certificate.
