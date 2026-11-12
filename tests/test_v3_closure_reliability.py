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


@pytest.mark.asyncio
async def test_fast_discovery_enables_known_controls_without_mutating_requests():
    from pathlib import Path
    from types import SimpleNamespace as NS
    from unittest.mock import AsyncMock
    from custom_components.audiconnect.v3.engine import V3Engine
    from custom_components.audiconnect.v3.registry import CapabilityRegistry
    from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
    from custom_components.audiconnect.v3.vehicle import V3Vehicle

    vin = "WAUZZZ4M0MD123456"
    root = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"
    model = CapabilityRegistry.from_json_file(root / "full_catalog.json")
    transport = NS(request=AsyncMock())
    engine = V3Engine(None, NS(entry_id="test"), model,
                      auth=NS(uses_auth0=True, service=NS(_spin="test")),
                      transport=transport, storage=NS(async_save=AsyncMock()))
    car = V3Vehicle(vin, "Audi", "Q8", "q8", "DE")
    car.advertised_capabilities = {"charging", "access"}
    engine.vehicles[vin.lower()] = car
    profile = DevelopmentProfile(model, car.context)
    engine.profiles[vin.lower()] = profile
    engine.commands.refresh_bindings()
    assert engine.control_enabled(vin, "start", "charging")
    assert profile.fast_bindings["charging.start"]["status"] == "catalog_matched"
    assert engine.control_enabled(vin, "lock", "access")
    assert profile.control_results == {}
    assert profile.active == {}
    car.impaired_capabilities.add("charging")
    assert not engine.control_enabled(vin, "start", "charging")
    profile.disable("access", "lock")
    assert not engine.control_enabled(vin, "lock", "access")
    transport.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_normal_command_persisted_before_dispatch_and_timeout_blocks_restart():
    from pathlib import Path
    from types import SimpleNamespace as NS
    from custom_components.audiconnect.v3.engine import V3Engine
    from custom_components.audiconnect.v3.registry import CapabilityRegistry
    from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
    from custom_components.audiconnect.v3.profile_store import restore_profile
    from custom_components.audiconnect.v3.vehicle import V3Vehicle

    vin = "WAUZZZ4M0MD123456"
    root = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"
    model = CapabilityRegistry.from_json_file(root / "full_catalog.json")
    car = V3Vehicle(vin, "Audi", "Q8", "q8", "DE")
    car.advertised_capabilities = {"charging"}
    saved = []
    calls = []
    class Storage:
        async def async_save(self, profiles):
            saved.append(profiles[vin.lower()].snapshot())
    class Transport:
        async def request(self, family, method, path, **kwargs):
            assert saved[-1]["last_command"]["state"] == "pending"
            calls.append(method)
            raise TimeoutError("synthetic")
    engine = V3Engine(None, NS(entry_id="test"), model,
                      auth=NS(uses_auth0=True, service=NS(_spin=None)),
                      transport=Transport(), storage=Storage())
    engine.vehicles[vin.lower()] = car
    engine.profiles[vin.lower()] = DevelopmentProfile(model, car.context)
    with pytest.raises(RuntimeError, match="uncertain"):
        await engine.send_control(vin, "start", "charging")
    assert calls == ["POST"]
    restored = restore_profile(model, car.context, saved[-1])
    assert restored.last_command.unresolved
    engine.profiles[vin.lower()] = restored
    with pytest.raises(RuntimeError, match="uncertain"):
        await engine.send_control(vin, "start", "charging")
    assert calls == ["POST"]
