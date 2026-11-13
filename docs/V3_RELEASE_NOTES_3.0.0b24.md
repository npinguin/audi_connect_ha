# Audi Connect 3.0.0b24 — climate continuity

Experimental fork prerelease. Source PR #25 at de2d3ba36cf86c2879f8992254a1f3267d1bc401. V2 remains default and fallback.

- Retain last valid, timestamped climate state in the existing private vehicle profile, including reboot and invalid OEM sentinel observations. Historical state is display-only; actual HVAC action requires fresh vehicle telemetry.
- Historical verified command or physically reviewed Workbench evidence can provide last-known state. HTTP acceptance alone does not verify actual state.
- Setpoint-only HA actions prefer the existing settings PUT when supported; no implicit climate start. Update both reported Celsius and Fahrenheit fields consistently, preserve other fields, never invent missing equipment flags.
- Temperature-bearing start requires both actual temperature and running-state readback before verification.
- Stale display does not suppress explicit climate start or stop.

No new vehicle endpoint or Q8-specific engine. The sparse Q8 settings shape is covered by tests; the PUT payload still requires physical acceptance on the actual vehicle. No automatic fallback or retry. Stable release remains blocked by physical acceptance and full feature closure.
