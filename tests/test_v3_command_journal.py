"""One command execution history for both normal and engineering actions."""
from pathlib import Path
from datetime import UTC, datetime

from custom_components.audiconnect.v3.command_journal import CommandRecord, HISTORY_LIMIT
from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
from custom_components.audiconnect.v3.profile_store import restore_profile
from custom_components.audiconnect.v3.registry import CapabilityRegistry, VehicleContext

ROOT = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"


def model():
    return CapabilityRegistry.from_json_file(ROOT / "full_catalog.json")


def test_shared_journal_survives_restart_without_replaying():
    p = DevelopmentProfile(model(), VehicleContext(auth="auth0", region="DE"))
    attempt = p.begin_test("charging", "start", "cariad.charging.start", now=10)
    p.observe_http(attempt.sequence, 200)
    p.confirm(attempt.sequence, worked=True, inspected_vehicle=True, now=20)
    p.track_command(CommandRecord.begin("charging", "stop", "cariad.charging.stop", 200))
    recovered = restore_profile(model(), p.discovery.context, p.snapshot())
    assert [record.origin for record in recovered.command_journal] == ["workbench", "home_assistant"]
    assert recovered.command_journal[0].state == "verified"
    assert recovered.last_command is recovered.command_journal[1]
    assert recovered.last_command.unresolved


def test_history_is_bounded():
    p = DevelopmentProfile(model(), VehicleContext(auth="auth0", region="DE"))
    for i in range(HISTORY_LIMIT + 5):
        record = CommandRecord.begin("charging", "start", "cariad.charging.start", i)
        record.state = "backend_completed"
        p.track_command(record)
    assert len(p.command_journal) == HISTORY_LIMIT
    recovered = restore_profile(model(), p.discovery.context, p.snapshot())
    assert len(recovered.command_journal) == HISTORY_LIMIT


def test_context_change_invalidates_evidence_but_preserves_pending_action():
    old = VehicleContext(auth="auth0", region="DE")
    new = VehicleContext(auth="auth0", region="BE")
    p = DevelopmentProfile(model(), old, cooldown_seconds=0)
    attempt = p.begin_test("charging", "start", "cariad.charging.start", now=10)
    p.observe_http(attempt.sequence, 200)
    restored = restore_profile(model(), new, p.snapshot())
    assert restored.discovery.context == new
    assert restored.discovery._active is not None
    assert restored.invalidated_attempt_sequence == attempt.sequence
    restored.confirm(attempt.sequence, worked=True, inspected_vehicle=True, now=20)
    assert restored.control_results == {}
    assert restored.active == {}
    assert restored.command_journal[-1].state == "verified"


def test_unresolved_capability_survives_unrelated_commands_and_restart():
    from custom_components.audiconnect.v3.command_journal import check_command_sequence, unresolved_normal_commands
    import pytest
    p = DevelopmentProfile(model(), VehicleContext(auth="auth0", region="DE"))
    uncertain = CommandRecord.begin("climate", "window_heating_start", "cariad.climate.window_heating_start", 1)
    uncertain.state = "uncertain"
    p.track_command(uncertain)
    check_command_sequence(p, 100, capability="access", action="lock")
    with pytest.raises(RuntimeError, match="uncertain"):
        check_command_sequence(p, 100, capability="climate", action="stop")
    for i in range(HISTORY_LIMIT + 2):
        other = CommandRecord.begin("access", "lock", "cariad.access.lock", 100+i*20)
        other.state = "verified"
        p.track_command(other)
    assert len(p.command_journal) == HISTORY_LIMIT
    restored = restore_profile(model(), p.discovery.context, p.snapshot())
    assert [row.command_id for row in unresolved_normal_commands(restored)] == [uncertain.command_id]
    with pytest.raises(RuntimeError, match="uncertain"):
        check_command_sequence(restored, 3000, capability="climate", action="start")
    check_command_sequence(restored, 3000, capability="charging", action="start")


def test_control_resolution_only_blocks_affected_capability():
    from types import SimpleNamespace as NS
    from custom_components.audiconnect.v3.control_resolution import control_decision
    from custom_components.audiconnect.v3.vehicle import V3Vehicle
    car = V3Vehicle("WAUZZZ4M0MD123456", "Audi", "Q8", "q8", "DE")
    car.auth_family = "auth0"
    car.advertised_capabilities.update({"access", "remoteLockUnlock", "charging"})
    p = DevelopmentProfile(model(), car.context)
    auth = NS(uses_auth0=True, service=NS(_spin="1234"))
    baseline = control_decision(car,p,auth,"access","lock")
    row = CommandRecord.begin("climate","window_heating_start","cariad.climate.window_heating_start",1)
    row.state = "uncertain"
    p.track_command(row)
    assert control_decision(car,p,auth,"access","lock") == baseline
    assert control_decision(car,p,auth,"climate","stop")["status"] == "pending_review"
