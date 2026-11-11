# Audi Connect V3 — Configuration, Testing & Rollback

## Before you start

This is an **experimental, in-place climate pilot**. Back up Home Assistant, note the existing Audi config entry and review automations that use `switch.climate_quick_control`. The V3 beta does not add a second Audi integration or request a new Audi login. **Do not uninstall/re-add the Audi integration to switch mode.** The package must be installed over the same `custom_components/audiconnect` directory, followed by a Home Assistant restart if files changed.

### Configuration via Home Assistant

**Settings → Devices & Services → Audi Connect → Configure / Options:**

| Setting | Default | Effect |
|---|---|---|
| Runtime generation | `v2` | Keeps original behavior; `v3_climate` activates one V3 climate entity per eligible Auth0 vehicle |
| V3 Climate start route | `auto` | Q8 trusted family → bodyless `cariad.climate.start.stored`; other Auth0 → settings adapter; explicit alternatives constrained by auth/model |
| V3 Climate status route | `auto` | Uses already scheduled selective-status batch; no separate periodic read |
| V3 Climate test when capability unknown | `false` | Manual action only when Audi inventory is missing; never bypass explicit denial/impaired |
| Scan interval | Existing value | One account-level polling coordinator |
| Refresh after action | Existing value | Existing request behavior; observe daily API limits |
| Climate quick start | Existing V2 setting | Relevant to V2 only; V3 has one reviewed start-path owner |

Settings are per integration entry and apply across that Audi account. Context scope is evaluated per vehicle, not stored as a duplicate vehicle profile. The private VIN stays inside the account.

### Example climate routing

```text
Audi Q8 PHEV + Europe + Auth0 + trusted Audi model
  STATUS: existing CARIAD selectivestatus batch
  START:  CARIAD bodyless start (vehicle-stored settings)
  STOP:   CARIAD bodyless stop
  TEMP:   no target-temperature feature advertised in V3

Another Auth0 model without Q8 proof
  STATUS: existing CARIAD batch
  START:  existing CARIAD settings adapter (only safe vehicle-reported target)
  STOP:   existing CARIAD stop
  TEMP:   no target-temperature control advertised in V3

Legacy MBB account
  Uses V2 climate for now. Do not silently route Auth0 commands with MBB tokens.
```

### How to test on the real car

1. Record vehicle state and myAudi status before the test. Avoid starting a test during a charging transition or while a previous command remains pending.
2. Start with V2 to record baseline ON/OFF, cloud request count, state capture time and any error. Do not blindly repeat unsuccessful car commands.
3. Select V3 Climate. Confirm there is **only one primary climate entity** with the same unique ID, no new duplicate quick switch, and no target temperature slider.
4. Run **one** explicit ON action only if the car supports it or you deliberately enabled the unknown-inventory experimental policy. Check myAudi and vehicle state separately. An acknowledged request alone is not proof of success.
5. After an appropriate normal cloud update, compare the climate status and source timestamps. Repeat for one OFF action after confirming the prior operation finished.
6. Download Audi Connect Diagnostics; inspect `runtime.v3` for chosen operations, context, local read evidence and rejection reasons. Check diagnostics contains no raw VIN or tokens.
7. Inspect the normal 15-minute (or configured) scan cycle: no extra polling or automatic wake. Verify legacy sensors and charger controls remain unaffected.
8. Roll back `Runtime generation` to `v2` via Options and verify climate works in its prior mode.

If no climate entity appears, check the Audi userCapabilities report, V3 diagnostics and old entity registry (do **not** immediately delete entities or re-add the account). If the status is stale or unsupported, the UI should say unknown/unavailable rather than claiming OFF.

### HACS/test distribution

HACS supports installing published GitHub releases and the repository default branch, not arbitrary feature branches as a guaranteed version selector. This beta must be **packaged as a GitHub prerelease at the exact tested commit**, with a tag that matches the `manifest.json` version (`3.0.0b1`), before it is advertised as a HACS version. The fork's Issues setting must be enabled for the HACS validation to pass. **Do not move the stable fork default branch to V3 to force distribution.**

Before a GitHub Release is published, advanced reviewers can manually copy only the tested branch's complete `custom_components/audiconnect` folder into their HA custom_components path, but that is **manual test installation**, not a HACS release.

### Rollback

First switch the runtime back to V2 using Options. If the installed package itself causes an integration startup failure, restore the previous V2 file package / HACS version from backup, restart Home Assistant and retain the original config entry. Do not delete device or entity registries. Record both package version and runtime mode in any bug report.

### Debug evidence to submit

Submit an anonymized report of firmware/model family (coarse), country/auth family, operation ID, HTTP code class, response schema/path presence, source freshness, actual user-observed actuation result, package version and option selection. **Never post VIN, user credentials, refresh tokens, exact location, raw trip data or full cloud response bodies publicly.**


### Minimum test environment and fork prerequisites

The V3 HACS candidate declares **Home Assistant 2026.7.0+** in
`hacs.json`; the Python test workflow uses Python 3.14. Test with a
compatible and backed-up HA instance. Because this is a fork, the experimental
manifest points to the fork's issues and configuration guide rather than
encouraging beta bug reports in upstream's stable support queue.

GitHub **Settings → General → Features → Issues** must be enabled in the
fork (currently disabled), then the HACS validation workflow rerun. A version
bump or draft PR alone does not make a valid installable HACS prerelease.


### Test-release versus stable rollout

After CI/HACS validation, a GitHub **prerelease** may be published for
controlled HACS evaluation. Install it on backed-up HA, then execute the
real Q8 test steps above. No physical result is assumed or certified at the
time the beta package becomes installable. Revert using the existing
integration Options first, then downgrade the package if needed.
