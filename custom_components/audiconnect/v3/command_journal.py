"""Bounded persistent execution journal shared by HA and Workbench commands."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from uuid import uuid4


_UNRESOLVED = frozenset({"pending", "uncertain"})
_STATES = _UNRESOLVED | {"accepted_unconfirmed", "backend_completed", "verified", "rejected", "reviewed", "physical_failed"}
HISTORY_LIMIT = 50
# Local anti-flood policy, not a claimed Audi server limit.
HA_COMMAND_COOLDOWN_SECONDS = 10
ENGINEERING_COMMAND_COOLDOWN_SECONDS = 90
_READBACKS = {"climate", "chargingState", "doorLockStatus", "targetstateOfCharge", "preferredChargeMode", "windowHeatingActive", "preheater_active",
              "climatisationWindowHeatingEnabled", "climatisationAtUnlock",
              "climatisationZoneFrontLeft", "climatisationZoneFrontRight",
              "climatisationZoneRearLeft", "climatisationZoneRearRight"}


@dataclass
class CommandRecord:
    command_id: str
    capability: str
    action: str
    operation: str
    started_at: float
    state: str = "pending"
    request_id: str | None = None
    readback_attribute: str | None = None
    readback_values: list | None = None
    origin: str = "home_assistant"
    engineering_sequence: int | None = None
    operation_revision: str | None = None
    backend_result: str | None = None
    completed_at: float | None = None
    parent_command_id: str | None = None

    @classmethod
    def begin(cls, capability: str, action: str, operation: str, now: float, **metadata):
        return cls(uuid4().hex, capability, action, operation, now, **metadata)

    @property
    def unresolved(self) -> bool:
        return self.state in _UNRESOLVED

    @property
    def is_wake(self) -> bool:
        """Only the reviewed CARIAD wake/refresh operations are preparatory."""
        return (self.capability == "remote" and self.action in ("wake", "refresh")
                and self.operation in ("cariad.remote.wake", "cariad.remote.refresh"))

    @property
    def wake_accepted(self) -> bool:
        return self.is_wake and self.state in ("accepted_unconfirmed", "backend_completed", "verified")

    def check_next(self, now: float, cooldown: float = HA_COMMAND_COOLDOWN_SECONDS, *, capability=None, action=None) -> None:
        if self.unresolved:
            raise RuntimeError("Previous vehicle command outcome uncertain; inspect and review it")
        if self.wake_accepted and capability is not None and action is not None:
            return  # Wake has its own quota/cadence guard in CommandEngine.
        if now < self.started_at + cooldown:
            # A user can explicitly stop a just-accepted comfort/charging
            # operation. No bypass for repeated starts, locks, engine or
            # unresolved commands; a subsequent start still waits.
            reversible = {
                ("climate", "start"): "stop",
                ("climate", "start_with_settings"): "stop",
                ("climate", "window_heating_start"): "window_heating_stop",
                ("charging", "start"): "stop",
                ("climate", "preheater_start"): "preheater_stop",
            }
            if (self.origin == "home_assistant" and self.state in
                    ("accepted_unconfirmed", "backend_completed", "verified")
                    and capability == self.capability
                    and reversible.get((self.capability, self.action)) == action
                    and action is not None):
                return
            remaining = math.ceil(self.started_at + cooldown - now)
            raise RuntimeError(f"Vehicle command cooldown active; try again in {remaining}s")

    def snapshot(self) -> dict:
        return asdict(self)

    @classmethod
    def restore(cls, value: dict, *, recover_pending: bool = True):
        if not isinstance(value, dict):
            raise ValueError("Invalid stored command context")
        try:
            record = cls(**value)
        except TypeError as exc:
            raise ValueError("Invalid stored command fields") from exc
        if (
            not isinstance(record.command_id, str) or len(record.command_id) != 32
            or any(c not in "0123456789abcdef" for c in record.command_id)
            or any(not isinstance(s, str) or not s or len(s) > 160
                   for s in (record.capability, record.action, record.operation))
            or type(record.started_at) not in (int, float)
            or not math.isfinite(record.started_at) or record.started_at < 0
            or record.state not in _STATES
            or record.origin not in ("home_assistant", "workbench")
            or (record.parent_command_id is not None and (
                not isinstance(record.parent_command_id, str)
                or not re.fullmatch(r"[a-f0-9]{32}", record.parent_command_id)
                or record.parent_command_id == record.command_id
                or record.capability != "remote" or record.action != "refresh"
                or record.origin != "home_assistant"))
            or (record.engineering_sequence is not None and (type(record.engineering_sequence) is not int or record.engineering_sequence < 1))
            or (record.origin == "workbench") != (record.engineering_sequence is not None)
            or (record.operation_revision is not None and (not isinstance(record.operation_revision, str) or not re.fullmatch(r"[a-f0-9]{64}", record.operation_revision)))
            or (record.backend_result is not None and record.backend_result not in ("accepted_unconfirmed", "backend_completed", "rejected", "unknown", "pending", "quota_limited", "transport_uncertain"))
            or (record.completed_at is not None and (type(record.completed_at) not in (int, float) or not math.isfinite(record.completed_at) or record.completed_at < record.started_at))
            or (record.request_id is not None and (not isinstance(record.request_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", record.request_id)))
            or (record.readback_attribute is not None and record.readback_attribute not in _READBACKS)
            or (record.readback_values is not None and (not isinstance(record.readback_values, list)
                or len(record.readback_values) > 8 or any(type(v) not in (str, int, bool) or len(str(v)) > 40
                    for v in record.readback_values)))
        ):
            raise ValueError("Invalid stored command context")
        if recover_pending and record.state in ("pending", "accepted_unconfirmed"):
            record.state = "uncertain"  # Never replay an interrupted mutation.
        return record


def check_command_sequence(profile, now: float, *, capability: str, action: str) -> None:
    """A preparatory wake cannot create or erase a real mutation cooldown.

    Uncertain latest commands remain blocking. When an accepted wake is the
    latest journal entry, recover the previous actual command's cooldown.
    Engineering tests retain their separate cooldown and review gates.
    """
    latest = profile.last_command
    if latest is None:
        return
    latest.check_next(now, capability=capability, action=action)
    if not latest.wake_accepted:
        return
    prior = next((record for record in reversed(profile.command_journal)
                  if record.origin == "home_assistant" and not record.is_wake), None)
    if prior is not None:
        prior.check_next(now, capability=capability, action=action)


def restore_history(rows):
    """Validate bounded private history; only the latest normal command can block."""
    if not isinstance(rows, list) or len(rows) > HISTORY_LIMIT:
        raise ValueError("Invalid command journal length")
    records = [CommandRecord.restore(row, recover_pending=False) for row in rows]
    if len({record.command_id for record in records}) != len(records):
        raise ValueError("Duplicate command journal ID")
    normal = next((record for record in reversed(records) if record.origin == "home_assistant"), None)
    if normal is not None and normal.state in ("pending", "accepted_unconfirmed"):
        normal.state = "uncertain"
    for record in records:
        if record.origin == "workbench" and record.state in ("pending", "accepted_unconfirmed"):
            record.state = "uncertain"
    return records, normal


def legacy_snapshot(record):
    """Original b8 last-command shape retained for older-reader compatibility."""
    keys = ("command_id", "capability", "action", "operation", "started_at", "state",
            "request_id", "readback_attribute", "readback_values")
    return {key: getattr(record, key) for key in keys}
