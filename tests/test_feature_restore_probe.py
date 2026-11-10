"""Feature-restore probes never run automatically or export vehicle data."""

from __future__ import annotations

import asyncio

import pytest
from aiohttp import ClientResponseError

from custom_components.audiconnect.api_probe import (
    FEATURE_RESTORE_PROBES,
    MAX_FEATURE_RESTORE_PROBES,
    RESTORE_PROBE_GROUPS,
    TRIP_DATA_PROBES,
    VEHICLE_HEALTH_PROBES,
    resolve_restore_probe_url,
    run_read_only_probes,
)
from custom_components.audiconnect.audi_services import AudiService

VIN = "SYNTHETICVIN000001"
TOKEN = "PRIVATE_TOKEN"


class FakeAPI:
    def __init__(self, remaining=30, statuses=None):
        self.vcf_remaining_calls = remaining
        self.statuses = list(statuses or [])
        self.calls = []
        self.token = None

    def use_token(self, token):
        self.token = token

    async def get(self, url):
        self.calls.append(url)
        if isinstance(self.vcf_remaining_calls, int):
            self.vcf_remaining_calls -= 1
        status = self.statuses.pop(0) if self.statuses else 200
        if status != 200:
            raise ClientResponseError(None, (), status=status)
        return {"data": [{"tripID": "PRIVATE_TRIP", "distance": 42.0}]}


def vehicle_url(suffix):
    return f"https://emea.bff.cariad.digital/vehicle/v1/vehicles/{VIN}/{suffix}"


def trip_url(kind):
    return f"https://emea.bff.cariad.digital/vehicle/v1/trips/{VIN}/{kind}"


def restoration_url(suffix):
    return resolve_restore_probe_url(suffix, vehicle_url, trip_url)


def run(api, **kwargs):
    return asyncio.run(
        run_read_only_probes(
            api,
            TOKEN,
            vehicle_url,
            restore=True,
            restore_url_for_route=restoration_url,
            **kwargs,
        )
    )


def test_trip_group_only_uses_three_proven_get_routes():
    api = FakeAPI()
    report = run(api)
    assert report["mode"] == "restore"
    assert report["restore_group"] == "trips"
    assert report["attempted"] == MAX_FEATURE_RESTORE_PROBES == 3
    assert len(api.calls) == len(TRIP_DATA_PROBES) == 3
    assert len(FEATURE_RESTORE_PROBES) == 6
    assert api.calls[0].endswith(f"/vehicle/v1/trips/{VIN}/shortterm")
    assert api.calls[1].endswith(f"/vehicle/v1/trips/{VIN}/longterm")
    assert api.calls[2].endswith(f"/vehicle/v1/trips/{VIN}/shortterm/last")
    assert all(url.startswith("https://emea.bff.cariad.digital/") for url in api.calls)
    assert report["mutating_requests"] == 0


def test_service_uses_current_bearer_without_login_or_mutation():
    api = FakeAPI()
    service = AudiService(api, "DE", None, 1)
    service._bearer_token_json = {"access_token": TOKEN}
    result = asyncio.run(
        service.probe_known_read_only_paths(VIN, restore=True)
    )
    assert result["mode"] == "restore"
    assert api.token == {"access_token": TOKEN}
    assert len(api.calls) == 3


def test_only_status_classification_survives_export():
    report = run(FakeAPI())
    output = repr(report)
    assert all(
        secret not in output
        for secret in (VIN, TOKEN, "PRIVATE_TRIP", "42.0")
    )
    assert all(
        set(row) <= {"probe", "outcome", "http_status", "reason"}
        for row in report["results"]
    )


@pytest.mark.parametrize("remaining", [0, 11, 12, 19])
def test_low_known_budget_prevents_all_network_requests(remaining):
    api = FakeAPI(remaining=remaining)
    report = run(api)
    assert api.calls == []
    assert report["attempted"] == 0
    assert all(row["outcome"] == "skipped" for row in report["results"])


def test_unknown_budget_allows_three_trip_requests_only():
    api = FakeAPI(remaining=None)
    report = run(api)
    assert report["attempted"] == 3
    assert len(api.calls) == 3
    assert [row["probe"] for row in report["results"]] == [
        "trip_shortterm",
        "trip_longterm",
        "trip_last",
    ]


def test_known_budget_reserves_twelve_calls():
    api = FakeAPI(remaining=20)
    report = run(api)
    assert report["attempted"] == 3
    assert api.vcf_remaining_calls == 17


@pytest.mark.parametrize(
    ("status", "classification"),
    [
        (401, "authentication_rejected"),
        (429, "rate_limited"),
        (502, "upstream_error"),
    ],
)
def test_critical_error_stops_remaining_calls(status, classification):
    api = FakeAPI(statuses=[status])
    report = run(api)
    assert len(api.calls) == 1
    assert report["results"][0]["outcome"] == classification
    assert all(row["outcome"] == "skipped" for row in report["results"][1:])


def test_404_is_unknown_route_not_negative_vehicle_capability():
    api = FakeAPI(statuses=[404])
    report = run(api)
    assert report["attempted"] == 3
    assert report["results"][0]["outcome"] == "route_not_found_or_not_provisioned"


def test_unrecognised_routes_are_refused_before_network():
    with pytest.raises(ValueError, match="Unrecognised"):
        restoration_url("trips:../../escape")
    with pytest.raises(ValueError, match="Unrecognised"):
        restoration_url("vehiclewakeup")


def test_old_core_probe_mode_and_absent_rate_limit_remain_unchanged():
    api = FakeAPI(remaining=None)
    result = asyncio.run(run_read_only_probes(api, TOKEN, vehicle_url))
    assert result["mode"] == "core"
    assert result["attempted"] == 8


def test_restore_and_extended_modes_are_mutually_exclusive():
    api = FakeAPI()
    with pytest.raises(ValueError, match="mutually exclusive"):
        run(api, extended=True)
    assert api.calls == []


def test_missing_restore_resolver_prevents_network_request():
    api = FakeAPI()
    with pytest.raises(ValueError, match="resolver"):
        asyncio.run(
            run_read_only_probes(
                api, TOKEN, vehicle_url, restore=True
            )
        )
    assert api.calls == []



def test_unknown_budget_still_stops_on_first_error():
    api = FakeAPI(remaining=None, statuses=[401])
    report = run(api)
    assert report["attempted"] == 1
    assert report["results"][0]["outcome"] == "authentication_rejected"
    assert len(api.calls) == 1


def test_vehicle_health_group_uses_all_three_read_only_jobs():
    api = FakeAPI(remaining=None)
    report = run(api, restore_group="vehicle_health")
    assert report["mode"] == "restore"
    assert report["restore_group"] == "vehicle_health"
    assert report["attempted"] == 3
    assert len(VEHICLE_HEALTH_PROBES) == 3
    assert [x["probe"] for x in report["results"]] == [
        "battery_support", "tyre_pressure", "vehicle_health_warnings"
    ]
    assert all("selectivestatus?jobs=" in url for url in api.calls)
    assert report["mutating_requests"] == 0


def test_restore_probe_group_validation_precedes_network():
    api = FakeAPI()
    with pytest.raises(ValueError, match="Unknown Audi restore probe group"):
        run(api, restore_group="nonexistent")
    with pytest.raises(ValueError, match="requires restore=true"):
        asyncio.run(
            run_read_only_probes(
                api, TOKEN, vehicle_url, restore_group="vehicle_health",
            )
        )
    assert not api.calls


def test_health_probe_unknown_budget_stops_after_first_401():
    api = FakeAPI(remaining=None, statuses=[401])
    result = run(api, restore_group="vehicle_health")
    assert len(api.calls) == 1
    assert result["results"][0]["outcome"] == "authentication_rejected"
    assert all(x["outcome"] == "skipped" for x in result["results"][1:])


def test_group_selection_matches_explicit_allowlist():
    assert RESTORE_PROBE_GROUPS == {
        "trips": TRIP_DATA_PROBES,
        "vehicle_health": VEHICLE_HEALTH_PROBES,
    }
    assert all("tripstatistics?type=" not in item[1] for item in FEATURE_RESTORE_PROBES)


def test_health_group_is_routed_through_real_audi_service():
    api = FakeAPI(remaining=None)
    service = AudiService(api, "DE", None, 1)
    service._bearer_token_json = {"access_token": TOKEN}
    report = asyncio.run(
        service.probe_known_read_only_paths(
            VIN, restore=True, restore_group="vehicle_health"
        )
    )
    assert report["restore_group"] == "vehicle_health"
    assert report["attempted"] == 3
    assert len(api.calls) == 3
    assert api.calls[0].endswith("selectivestatus?jobs=batterySupport")
    assert api.calls[1].endswith("selectivestatus?jobs=tyrePressure")
    assert api.calls[2].endswith("selectivestatus?jobs=vehicleHealthWarnings")
    assert all(url.startswith("https://emea.bff.cariad.digital/") for url in api.calls)
    assert api.token == {"access_token": TOKEN}


def test_health_job_http_200_without_matching_job_does_not_claim_data():
    api = FakeAPI(remaining=None)
    report = run(api, restore_group="vehicle_health")
    assert all(x["outcome"] == "job_missing_from_response" for x in report["results"])
    assert report["mutating_requests"] == 0
