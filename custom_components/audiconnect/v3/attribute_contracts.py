"""Home Assistant-standard sensor metadata stored as declarative V3 contracts.

Extracted from V2 sensor descriptions. Values with unknown/dynamic units are
intentionally not guessed; route definitions may later supply a proven unit.
"""
from __future__ import annotations
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

@lru_cache(maxsize=1)
def attribute_contracts() -> dict[str, dict[str, Any]]:
    document = json.loads(Path(__file__).with_name("attribute_contracts.json").read_text())
    if document.get("schema_version") != 1 or not isinstance(document.get("attributes"), dict):
        raise ValueError("Invalid Audi V3 attribute contract")
    return document["attributes"]

def contract_for(entity_key: str) -> dict[str, Any]:
    return attribute_contracts().get(entity_key, {})
