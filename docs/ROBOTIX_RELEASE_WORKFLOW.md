# Robotix Audi Connect — branching & release rules

Upstream source: `audiconnect/audi_connect_ha` v2.5.2.

## Branches
- `master`: currently fork's inherited upstream baseline. Do not deploy from here after Robotix customizations begin.
- `main`: release branch. Merge only tested, documented changes.
- `fix/q8-auth0-command-safety`: **persistent development branch**. Do not delete on merge. Continue to add improvements and prepare subsequent PRs.

Change the GitHub default branch to `main` when the fork is ready to become its own Marketplace source (GitHub Settings → Default branch). This cannot be done through the current connector.

## Test-release rule

1. All source changes land on the development branch.
2. Tests: `pytest` on supported Python, `hassfest` and HACS/Marketplace validation.
3. Manual smoke test: native HA diagnostic download; API probe results; entity ID continuity; no auto actuator calls; rollback.
4. Bump `custom_components/audiconnect/manifest.json` to a new **never-reused** pre-release version, for example `2.5.3b1`.
5. Merge the validated snapshot from the development branch to `main`. Keep the development branch.
6. The Robotix prerelease workflow runs automatically when the validated version bump is merged to `main` (or manually dispatched). It checks the exact beta manifest version. It validates again, tags the exact main commit and publishes a GitHub pre-release with ZIP assets:
   - `audiconnect-ha-install.zip` for copying under `/config/custom_components` (contains `audiconnect/`)
   - `audiconnect-hacs.zip` for a flat release archive, if later configured for zip-based HACS downloads.
7. Keep `hacs.json` in source mode while Marketplace compatibility is validated; Marketplace/HACS can use a release tag as source. Do not set `zip_release` without verifying the expected layout in both clients.
8. **Do not uninstall the Audi config entry** to switch the repository owner; the new Marketplace can delete vehicle/device/entity registration as part of uninstall. Back up HA first and validate a non-destructive replacement.

## Release gating

No release based solely on static tests. At minimum, target HA must show active Auth0 session, current vehicle data, read-only API-probe classification (or explicit documented non-tested status), no raw VIN/token in downloadable diagnostics, Q8 engine-action protection, and no regression in chargers/climate.

A 200/202 API response is gateway acceptance, not confirmed execution by the car. No unsafe actuator tests in automated CI.

The inherited upstream scheduled `release.yml` workflow must not be used for Robotix releases. Replace or disable its schedule before changing the repository default branch to `main`. Use only manually approved prereleases.


**Beta 2:** `2.5.3b2` adds manual local dealership/service metadata, an optional 12-read extended API probe and an anonymized capability catalogue. HAR cookies/tokens are never committed; verify the new local-dealer sensor and preservation across OptionsFlow edits in HA runtime before considering production use.
