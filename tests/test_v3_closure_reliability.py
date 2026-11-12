"""Architecture-closure regressions: no real Audi requests."""
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.audiconnect.v3.quota import QuotaBudget
from custom_components.audiconnect.v3.command_journal import CommandRecord


def test_exhausted_budget_allows_only_one_bounded_recovery_read():
    now = datetime(2026, 11, 12, tzinfo=UTC)
    budget = QuotaBudget()
    budget.observe(200, {"Vcf-Remaining-Calls": "8"}, now)
    with pytest.raises(RuntimeError):
        budget.authorize(now, read_only=True)
    later = now + timedelta(hours=1)
    with pytest.raises(RuntimeError):
        budget.authorize(later, read_only=False)
    budget.authorize(later, read_only=True)
    with pytest.raises(RuntimeError):
        budget.authorize(later, read_only=True)
    # A response without quota evidence must not reset an exhausted reserve.
    budget.observe(200, {}, later)
    with pytest.raises(RuntimeError):
        budget.authorize(later, read_only=False)
    budget.observe(200, {"Vcf-Remaining-Calls": "42"}, later)
    budget.authorize(later, read_only=False)


def test_retry_after_honored_and_recovery_never_mutates():
    now = datetime(2026, 11, 12, tzinfo=UTC)
    budget = QuotaBudget()
    budget.observe(429, {"Retry-After": "7200"}, now)
    with pytest.raises(RuntimeError):
        budget.authorize(now + timedelta(hours=1), read_only=True)
    with pytest.raises(RuntimeError):
        budget.authorize(now + timedelta(hours=2), read_only=False)
    budget.authorize(now + timedelta(hours=2), read_only=True)


def test_pending_command_restores_uncertainty_without_replay():
    record = CommandRecord.begin("charging", "start", "cariad.charging.start", 1000)
    restored = CommandRecord.restore(record.snapshot())
    assert restored.command_id == record.command_id
    assert restored.unresolved
    with pytest.raises(RuntimeError, match="uncertain"):
        restored.check_next(2000)
    restored.state = "reviewed"
    restored.check_next(2000)


def test_completed_command_cooldown_survives_restart():
    record = CommandRecord.begin("climate", "stop", "cariad.climate.stop", 1000)
    record.state = "backend_completed"
    restored = CommandRecord.restore(record.snapshot())
    with pytest.raises(RuntimeError, match="cooldown"):
        restored.check_next(1089)
    restored.check_next(1090)


def test_status_evidence_roundtrips_for_non_climate_capability():
    from pathlib import Path
    from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
    from custom_components.audiconnect.v3.profile_store import restore_profile
    from custom_components.audiconnect.v3.registry import CapabilityRegistry, VehicleContext

    root = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"
    catalog = CapabilityRegistry.from_json_file(root / "full_catalog.json")
    context = VehicleContext(auth="auth0", region="DE")
    profile = DevelopmentProfile(catalog, context)
    operation = "cariad.status.charging"
    assert profile.record_status("charging", operation, http_status=200,
                                 schema_valid=True, fresh=True) == "worked"
    profile.choose_working("charging", "status", operation)
    restored = restore_profile(catalog, context, profile.snapshot())
    assert restored.active["charging.status"] == operation


def test_engine_composes_status_and_command_owners():
    from pathlib import Path
    import ast
    root = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"
    for name in ("status_engine.py", "command_engine.py"):
        tree = ast.parse((root / name).read_text())
        assert not any(isinstance(node, ast.ImportFrom) and node.module == "engine"
                       for node in ast.walk(tree))
    source = (root / "engine.py").read_text()
    assert "self.status = StatusEngine(" in source
    assert "self.commands = CommandEngine(" in source
