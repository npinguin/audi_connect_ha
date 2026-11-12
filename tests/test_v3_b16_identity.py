from datetime import UTC, datetime
from custom_components.audiconnect.v3.transport import (
    V3Response, selected_identity_response, IDENTITY_QUERIES,
)

def test_graphql_partial_errors_are_scoped_and_safe():
    vin = "WAUZZZ4M0MD123456"
    other = "WAUZZZ4M0MD123457"
    response = V3Response(200, {"data":{"userVehicles":[
        {"vin":vin,"vehicle":{"core":None,"renderPictures":[{"mediaType":"MYAPN8NB","url":"private-url"}]}},
        {"vin":other,"vehicle":{"media":{"longName":"Other model"}}}]},
        "errors":[{"message":"private","path":["userVehicles",0,"vehicle","core"],
                   "extensions":{"code":"INTERNAL_SERVER_ERROR"}},
                  {"path":["userVehicles",1,"vehicle","media"],"extensions":{"code":"FORBIDDEN"}}]}, datetime.now(UTC))
    selected = selected_identity_response(response, vin)
    assert selected.data["errors"] == [{"code":"INTERNAL_SERVER_ERROR","field":"userVehicles.vehicle.core"}]
    assert other not in str(selected.data) and "private-url" not in str(selected.data)
    assert "private" not in str(selected.data)
    assert len(IDENTITY_QUERIES) == 4
