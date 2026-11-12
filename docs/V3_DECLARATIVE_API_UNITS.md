# Audi V3 — declarative response and sensor contracts

A source API family defines the JSON response path and, **only when proven**,
a `conversion` object with `unit_class`, `from`, and `to`. V3 delegates
conversion to Home Assistant's standard unit converters. No arbitrary Python,
percentage heuristics, unit guessing, or per-vehicle entity calculations.

The independent `attribute_contracts.json` specifies the *normalized* HA
sensor's `native_unit_of_measurement`, `device_class`, `state_class`,
`suggested_display_precision`, and diagnostic category. It was transcribed
from the stable V2 sensor descriptions. Missing metadata remains null, not
invented.

`api_value_mappings.json` is an intentionally sparse map of verified source
conversions by family and attribute. Absence means identity, never an implicit
scale. A custom GET route may declare its own validated `conversion`.
The existing historical V2 response-path catalog remains source-of-truth
for recognized fields. `0` and `false` must survive extraction.

Examples of safe route metadata (do not apply blindly):
```json
{"unit_class":"power","from":"W","to":"kW"}
{"unit_class":"distance","from":"mi","to":"km"}
```

Do not activate a transform until the raw unit is confirmed in a saved
redacted API response and matches the destination contract. The two
historical V2 dynamic units (charge rate and remaining charge time) are
marked `unit_resolution: api_route`, not hardcoded as A/min.
\nResponse selectors also accept the standard **RFC 6901 JSON Pointer**
(e.g. `/charging/batteryStatus/value/currentSOC_pct`). Existing dotted V2
paths remain supported for compatibility. The same extraction helper is used
for registered operations and per-attribute route mapping. A converter's
destination unit must match the HA attribute contract; an API cannot
reinterpret SoC as distance.\n