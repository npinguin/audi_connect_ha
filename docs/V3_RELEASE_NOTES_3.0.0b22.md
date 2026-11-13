# Audi Connect 3.0.0b22 — ownership closure

Experimental fork prerelease for Home Assistant acceptance testing. Based on the ownership review PR #23, runtime source a0896ba20191f18c713493e525171b7e79010830. V2 remains the default and fallback; V3 remains opt-in.

- Resolve services to their owning loaded account and vehicle.
- Consolidate authentication, reviewed read templates and command input validation.
- Use the native product contract for control projection and diagnostics.
- Preserve registry identity and user settings; reverse owned name migrations on rollback.
- Remove entry-owned profiles, trips and migration storage only on explicit integration removal.
- Restrict the Workbench to loaded opted-in V3 entries; copy portable saved route definitions without evidence or automatic activation.

Back up Home Assistant before testing. Validate V2/V3/V2 migration, entity availability, real vehicle readings, commands and their actual readback. OEM support and full physical acceptance remain unproven; do not rely on stale access or charging telemetry as current physical safety evidence. No stable promotion or upstream merge is implied.

The packaging workflow checks exact runtime equivalence except the version, tests HA 2026.7.0 and 2026.11.1, Workbench, pre-commit, HACS and hassfest, verifies ZIP checksum, and requires merged fork PR #23 at the pinned head before publication.
