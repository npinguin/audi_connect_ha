"""Prevent next-release authorization from bypassing the completeness audit."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_completeness_gate_is_explicit_and_next_beta_cannot_skip_open_blockers():
    gate=json.loads((ROOT/"governance/V3_COMPLETENESS_GATE.json").read_text())
    manifest=json.loads((ROOT/"custom_components/audiconnect/manifest.json").read_text())
    items=gate["items"]
    assert len({item["id"] for item in items})==len(items)
    assert {item["status"] for item in items} <= {"open","implemented_pending_validation","closed"}
    assert all(item["acceptance"] and type(item["blocks_hacs"]) is bool and
               type(item["blocks_upstream"]) is bool for item in items)
    assert gate["hacs_ready"] == all(item["status"]=="closed" for item in items if item["blocks_hacs"])
    assert gate["upstream_ready"] == all(item["status"]=="closed" for item in items if item["blocks_upstream"])
    if manifest["version"] != gate["baseline"]:
        assert gate["hacs_ready"], "Completeness audit has open HACS blockers"
    assert all(item.get("closure_evidence") for item in items if item["status"]=="closed")

def test_b12_evidence_does_not_conflate_http_and_physical_verification():
    evidence=json.loads((ROOT/"docs/V3_COMPLETENESS_EVIDENCE_B12.json").read_text())
    assert evidence["observed_jobs"]+evidence["not_observed_jobs"]==evidence["catalog_jobs"]
    assert evidence["schema_truncated"] is True
    assert all(row["disposition"] and row["target"] for row in evidence["fields"])
    physical={(row["capability"],row["action"]) for row in evidence["controls"]
              if row["physical_evidence"]=="worked"}
    assert physical=={("climate","start"),("climate","stop")}
    assert all("value" not in row for row in evidence["fields"])
