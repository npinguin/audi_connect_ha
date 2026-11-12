from datetime import UTC, datetime
from types import SimpleNamespace
import pytest
from custom_components.audiconnect.v3.transport import V3Response, selected_garage_response, GARAGE_OPERATION, identity_errors
from custom_components.audiconnect.v3.vehicle import V3Vehicle
from custom_components.audiconnect.v3.identity_cache import capture_identity, apply_cached_identity
from custom_components.audiconnect.v3.family_executors import CARIADExecutor

VIN = "WAUZZZ4M0MD123456"
OTHER = "WAUZZZ4M0MD123457"

def test_garage_scoped_identity_and_cache():
    response = V3Response(200, {"data":[{"vin":VIN,"model":"Audi Q8", "modelYear":2022,
        "nickname":"personal", "carnetAllocationType":"unknown"}, {"vin":OTHER,"model":"Other"}]}, datetime.now(UTC))
    selected = selected_garage_response(response, VIN)
    assert OTHER not in str(selected.data) and "personal" not in str(selected.data)
    car = V3Vehicle.from_garage(selected.data["data"][0], "DE")
    assert car.model == "Audi Q8" and car.model_year == "2022"
    assert car.identity_operation == GARAGE_OPERATION and car.car_type == ""
    car.identity_observed_at = datetime.now(UTC).isoformat()
    saved = capture_identity(car)
    restored = V3Vehicle(VIN, "Audi vehicle", "", "", "DE")
    apply_cached_identity(restored, saved)
    assert restored.model == car.model and restored.identity_operation == GARAGE_OPERATION
    assert restored.identity_restored and not restored.car_type

def test_no_model_from_nickname_or_vin():
    car = V3Vehicle.from_garage({"vin":VIN,"model":VIN,"nickname":"Q8","modelYear":2022}, "DE")
    assert not car.model and car.model_year == "2022"

def test_garage_only_read():
    auth = SimpleNamespace(uses_auth0=True,country="DE", access_token=lambda family:"fake")
    plan = CARIADExecutor().plan(auth, "GET", "/vehicle/v1/vehicles")
    assert plan.url == "https://emea.bff.cariad.digital/vehicle/v1/vehicles"
    for method,path in [("POST","/vehicle/v1/vehicles"),("GET","/vehicle/v1/vehicles?foo=1")]:
        with pytest.raises(ValueError):
            CARIADExecutor().plan(auth, method, path, explicit_action=True)

def test_graphql_exchange_denial_classification():
    result = identity_errors({"errors":[{"message":"client does not have access to the IDP for token exchange: private",
                 "extensions":{"code":"FORBIDDEN"}}]}, VIN)
    assert result == [{"code":"FORBIDDEN","field":"","reason":"token_exchange_denied"}]
