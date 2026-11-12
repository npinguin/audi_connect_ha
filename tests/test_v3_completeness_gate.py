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
        if not gate["hacs_ready"]:
            # Explicit, version-specific evidence-acquisition exception only.
            assert manifest["version"] == "3.0.0b13", "Completeness audit has open HACS blockers"
            auth = json.loads((ROOT/"governance/B13_EXPERIMENTAL_TEST_RELEASE.json").read_text())
            exception = auth["completeness_exception"]
            pending = [item for item in items if item["blocks_hacs"] and item["status"] != "closed"]
            assert auth["version"] == exception["version"] == manifest["version"]
            assert auth["classification"] == "experimental_hacs_test_only"
            assert auth["stable_promotion_allowed"] is False
            assert auth["static_parity_claimed"] is False
            assert exception["upstream_gate_override"] is False
            assert exception["allows_open_implementation_blockers"] is False
            assert exception["requires_status"] == "implemented_pending_validation"
            assert {item["id"] for item in pending} == set(exception["pending_hacs_gate_ids"])
            assert all(item["status"] == "implemented_pending_validation" and item.get("implementation_evidence") for item in pending)
            assert gate["upstream_ready"] is False
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


def test_upstream_feature_matrix_matches_canonical_catalog_without_claiming_live_acceptance():
    matrix=json.loads((ROOT/"docs/V3_UPSTREAM_FEATURE_MATRIX.json").read_text())
    catalog=json.loads((ROOT/"custom_components/audiconnect/v3/full_catalog.json").read_text())
    product=json.loads((ROOT/"custom_components/audiconnect/v3/product_entities.json").read_text())
    baseline=json.loads((ROOT/"docs/V3_COMPLETENESS_EVIDENCE_B12.json").read_text())
    assert {row["id"] for row in matrix["entities"]} == set(product["entities"])
    assert {row["id"] for row in matrix["operations"]} == set(catalog["operations"])
    assert {(row["capability"],row["action"]) for row in matrix["controls"]} == {
        (capability,action) for capability,definition in catalog["capabilities"].items()
        for action in definition.get("control", {})}
    assert len(matrix["observed_b12_fields"]) == len(baseline["fields"])
    assert all(row["review_disposition"] != "open" for row in matrix["observed_b12_fields"])
    assert all(row["b13_physical"] == "not_tested_on_b13" for row in matrix["controls"])
    assert all(row["b13_live"] == "not_validated" for row in matrix["operations"])
    assert all((ROOT/path).is_file() for row in matrix["capabilities"] for path in row["fixture_review_files"])
