"""Admin-only reverse index from product and mapping contracts."""
from .product_contract import product_inventory

def link_entities(report, actual, inventory=None):
    inventory = product_inventory()["entities"] if inventory is None else inventory
    by_key = {key: {"contract_key": key, "entity_ids": sorted(set(ids)),
                    "capabilities": set(), "attributes": set(), "operations": set()}
              for key, ids in actual.items()}
    rows = report.get("rows", [])
    for operation in report.get("operations", []):
        for mapping in operation.get("mappings", []):
            key = mapping.get("entity_key")
            mapping["entity_ids"] = sorted(set(actual.get(key, [])))
            if key not in by_key:
                continue
            entry = by_key[key]
            if mapping.get("capability"):
                entry["capabilities"].add(mapping["capability"])
            if mapping.get("attribute"):
                entry["attributes"].add(mapping["attribute"])
            entry["operations"].add(operation["operation"])
    for key, entry in by_key.items():
        sources = set(inventory.get(key, {}).get("source_attributes", []))
        for row in rows:
            if row.get("attribute") not in sources or not row.get("entity_key"):
                continue
            entry["attributes"].add(row["attribute"])
            entry["capabilities"].add(row["capability"])
            if row.get("operation"):
                entry["operations"].add(row["operation"])
        if not entry["capabilities"] and key in {
            "sensor.vehicle_data_freshness", "sensor.vehicle_data_age",
            "sensor.cloud_last_successful_poll", "sensor.api_requests_remaining",
            "sensor.discovery_coverage", "sensor.integration_status", "sensor.last_error",
            "binary_sensor.integration_problem", "button.v3_refresh_cloud",
        }:
            entry["capabilities"].add("integration_health")
        if key in ("sensor.door_status", "sensor.window_status"):
            entry["capabilities"].add("access")
        if key in ("device_tracker.position", "sensor.last_trip", "sensor.trip_history") or inventory.get(key, {}).get("trip_metric"):
            entry["capabilities"].add("mobility")
        for field in ("capabilities", "attributes", "operations"):
            entry[field] = sorted(entry[field])
    for row in rows:
        key = f'{row.get("platform")}.{row.get("entity_key")}'
        row["entity_ids"] = sorted({eid for entry in by_key.values()
                                   if entry["contract_key"] == key or (
                                       row.get("entity_key") and row.get("attribute") in entry["attributes"]
                                       and row.get("capability") in entry["capabilities"])
                                   for eid in entry["entity_ids"]})
    for action in report.get("control_actions", []):
        action["entity_ids"] = sorted({eid for entry in by_key.values()
                                      if action.get("capability") in entry["capabilities"]
                                      and "control." + str(action.get("action")) in entry["attributes"]
                                      for eid in entry["entity_ids"]})
    report["entity_links"] = sorted(by_key.values(), key=lambda item: item["contract_key"])
    return report
