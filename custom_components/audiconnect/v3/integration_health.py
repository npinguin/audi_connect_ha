"""Bounded, value-free operational findings; no extra API requests."""
from datetime import UTC, datetime

from .historical_catalog import V2_JOBS

HEALTH_STATES = ["initializing", "operational", "degraded", "rate_limited",
                 "authentication_required", "cloud_unavailable", "error"]


class IntegrationHealth:
    def __init__(self):
        self.findings = {}
        self.last = {}
        self.poll_error = None

    def _record(self, vehicle, key, code, *, http=None, oem=None, retry=None):
        rows = self.findings.setdefault(vehicle, {})
        previous = rows.get(key)
        now = datetime.now(UTC).isoformat()
        row = {"code": code, "source": key, "http_status": http, "oem_error_code": oem,
               "retryable": retry, "active": True,
               "first_seen": previous["first_seen"] if previous else now,
               "last_seen": now, "occurrences": previous["occurrences"] + 1 if previous else 1}
        rows[key] = row
        if len(rows) > 32:
            rows.pop(next(iter(rows)))
        self.last[vehicle] = row

    def _recover(self, vehicle, key):
        row = self.findings.get(vehicle, {}).pop(key, None)
        if row is not None and self.last.get(vehicle) is row:
            self.last[vehicle] = {**row, "active": False, "recovered_at": datetime.now(UTC).isoformat()}

    def observe(self, vehicle, operation, method, response, operations):
        discovery = operation.startswith("cariad.discovery.")
        jobs = operation.removeprefix("cariad.discovery.").split("_") if discovery else []
        if operation not in operations and not (discovery and jobs and all(j in V2_JOBS for j in jobs)):
            return
        if method != "GET" and operation != "graphql.inventory.vehicleList":
            return
        status = getattr(response, "status", None)
        if status is None or not 200 <= status < 300:
            self._record(vehicle, operation, "api_request_failed", http=status)
            return
        self._recover(vehicle, operation)
        data = response.data
        if not isinstance(data, dict):
            return
        for job in V2_JOBS:
            value = data.get(job)
            if not isinstance(value, dict):
                continue
            candidates = [value, *[v for v in value.values() if isinstance(v, dict)]]
            errors = [v["error"] for v in candidates if isinstance(v.get("error"), dict)]
            if errors:
                error = errors[0]
                code = error.get("code")
                self._record(vehicle, job, "api_partial_response", http=status,
                             oem=code if type(code) is int and 0 <= code <= 2147483647 else None,
                             retry=error.get("retry") if type(error.get("retry")) is bool else None)
            elif any(v.get("value") not in (None, {}, []) for v in candidates):
                self._recover(vehicle, job)

    def snapshot(self, engine, car):
        key = car.vin.lower()
        findings = list(self.findings.get(key, {}).values())
        remaining = getattr(engine.transport, "remaining_calls", None)
        quota = getattr(engine.transport, "quota", None)
        retry_at = getattr(quota, "retry_at", None)
        limited = ((remaining is not None and remaining <= getattr(quota, "reserve", 8))
                   or (retry_at is not None and retry_at > datetime.now(UTC)))
        poll = engine.last_cloud_poll_succeeded
        identity = "last_known" if car.identity_restored else "observed" if car.model else "missing"
        if self.poll_error == "authentication_required":
            state = self.poll_error
        elif limited:
            state = "rate_limited"
        elif self.poll_error == "error":
            state = "error"
        elif poll is False or self.poll_error == "cloud_unavailable":
            state = "cloud_unavailable"
        elif poll is None:
            state = "initializing"
        elif findings or identity != "observed" or not car.inventory_present:
            state = "degraded"
        else:
            state = "operational"
        last = self.last.get(key)
        return {"status": state, "problem": state in ("degraded", "rate_limited",
                "authentication_required", "cloud_unavailable", "error"),
                "cloud_poll_succeeded": poll, "quota_remaining": remaining,
                "identity_status": identity, "active_findings": findings,
                "active_error_count": len(findings),
                "last_error": dict(last) if last else None, "poll_error": self.poll_error}
