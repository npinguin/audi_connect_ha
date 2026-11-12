import pytest
from custom_components.audiconnect.v3.transport import validate_identity_query

@pytest.mark.parametrize("query", [
    "query vehicleList { userVehicles { vin vehicle { media { longName } } } }",
    "{ userVehicles { vin vehicle { core { modelYear } newField } } }",
])
def test_read_only_query_editor_accepts_selection(query):
    validate_identity_query(query)

@pytest.mark.parametrize("query", [
    "mutation { userVehicles { vin } }",
    "{ userVehicles { vehicle { core { modelYear } } } }",
    "{ userVehicles { vin alias: vehicle { core { modelYear } } } }",
    "{ userVehicles { vin } } { userVehicles { vin } }",
    "{ userVehicles { vin __typename } }",
    "{ userVehicles { vin vehicle(arg: 1) { core } } }",
    "{ userVehicles { vin @skip(if: true) } }",
    "{ userVehicles { vin } account { email } }",
])
def test_read_only_query_editor_rejects_unscoped_or_nonselection(query):
    with pytest.raises(ValueError):
        validate_identity_query(query)
