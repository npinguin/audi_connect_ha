"""V3 safe response preview rules."""
from __future__ import annotations

import json

from custom_components.audiconnect.v3.response_preview import safe_response_preview


def test_nested_climate_response_is_readable():
    observed = {
        "climatisation": {
            "climatisationStatus": {
                "value": {
                    "climatisationState": "off",
                    "carCapturedTimestamp": "2026-11-11T14:00:00Z",
                }
            }
        }
    }
    preview = safe_response_preview(observed)
    assert preview["climatisation"]["climatisationStatus"]["value"][
        "climatisationState"
    ] == "off"


def test_response_preview_never_exposes_vin_auth_or_coordinates():
    vin = "WAUZZZ4M0MD123456"
    value = {
        "vin": vin,
        "url": "https://example.org/vehicle/" + vin,
        "authorization": "Bearer TEST",
        "location": {"latitude": 50, "longitude": 4},
        "nested": {"refresh_token": "BAD", "state": "heating"},
    }
    report = json.dumps(safe_response_preview(value, vehicle_vin=vin))
    assert vin not in report
    assert "Bearer TEST" not in report
    assert '"latitude"' not in report
    assert '"refresh_token": "BAD"' not in report
    assert "heating" in report


def test_truncated_long_response_is_bounded():
    report = json.dumps(safe_response_preview({
        "list": [{"v": "x" * 800} for _ in range(100)]
    }))
    assert len(report) < 2800
    assert "more items omitted" in report
