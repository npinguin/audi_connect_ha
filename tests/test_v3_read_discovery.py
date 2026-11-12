"""Automated CARIAD GET discovery keeps absent fields as inconclusive, not unsupported."""
from types import SimpleNamespace
from custom_components.audiconnect.v3.read_discovery import (
    record_jobs, pending_groups, reserve_group, summary,
)
from custom_components.audiconnect.v3.historical_catalog import V2_JOBS


def blank_profile():
    return SimpleNamespace(job_discovery={}, job_probe_attempts={}, attribute_evidence={})


def test_startup_shared_status_observes_jobs_but_missing_is_not_unsupported():
    profile = blank_profile()
    record_jobs(profile, V2_JOBS, status=200, payload={
        "charging":{"batteryStatus":{"value":{"currentSOC_pct":40}}}
    })
    assert profile.job_discovery["charging"] == "observed"
    assert profile.job_discovery["climatisation"] == "not_observed"
    assert summary(profile)["not_scanned_jobs"] == 0
    assert summary(profile)["catalog_jobs"] == 23
    first=pending_groups(profile, max_groups=2)
    assert first[0] == ("climatisation",)
    assert len(first) == 2


def test_group_probe_is_bounded_does_not_repeat_or_auto_mutate():
    profile=blank_profile()
    profile.job_discovery={"climatisation":"not_observed", "charging":"not_observed"}
    selected=pending_groups(profile,max_groups=1)
    assert selected == [("climatisation",)]
    reserve_group(profile,selected[0])
    assert pending_groups(profile,max_groups=1)[0] == ("charging",)
    assert profile.job_probe_attempts["climatisation"]==1
    assert all(job in V2_JOBS for job in profile.job_probe_attempts)


def test_transient_api_errors_cannot_mark_a_supported_job_missing():
    profile=blank_profile()
    record_jobs(profile, ("charging",), status=429, payload=None)
    assert profile.job_discovery["charging"] == "inconclusive"
    record_jobs(profile, ("charging",), status=200, payload={"charging":{"status":"ok"}})
    assert profile.job_discovery["charging"] == "not_observed"
    record_jobs(profile, ("charging",), status=207, payload={
        "charging":{"batteryStatus":{"value":{"currentSOC_pct":42}}}
    })
    assert profile.job_discovery["charging"] == "observed"
    record_jobs(profile, ("charging",), status=503, payload=None)
    assert profile.job_discovery["charging"] == "observed"

def test_automatic_probe_plan_covers_every_known_missing_job():
    profile = blank_profile()
    attempted = set()
    while groups := pending_groups(profile, max_groups=2):
        for group in groups:
            assert not attempted.intersection(group)
            attempted.update(group)
            reserve_group(profile, group)
    assert attempted == set(V2_JOBS)


def test_active_ventilation_timer_namespace_is_read_evidence():
    profile = blank_profile()
    record_jobs(profile, ("activeVentilation",), status=207, payload={
        "climatisationTimers": {"activeVentilationTimersStatus": {"value": {
            "timers": [{"id": 1, "enabled": False}]}}}
    })
    assert profile.job_discovery["activeVentilation"] == "observed"
    assert "climatisation" not in profile.job_discovery
