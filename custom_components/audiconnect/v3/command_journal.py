"""Persistent normal-command context; no credentials, request bodies or VINs."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from uuid import uuid4


_UNRESOLVED = frozenset({"pending", "uncertain"})
_STATES = _UNRESOLVED | {"accepted_unconfirmed", "backend_completed", "rejected", "reviewed"}


@dataclass
class CommandRecord:
    command_id: str
    capability: str
    action: str
    operation: str
    started_at: float
    state: str = "pending"

    @classmethod
    def begin(cls, capability: str, action: str, operation: str, now: float):
        return cls(uuid4().hex, capability, action, operation, now)

    @property
    def unresolved(self) -> bool:
        return self.state in _UNRESOLVED

    def check_next(self, now: float, cooldown: float = 90) -> None:
        if self.unresolved:
            raise RuntimeError("Previous vehicle command outcome uncertain; inspect and review it")
        if now < self.started_at + cooldown:
            raise RuntimeError("Vehicle command cooldown active; verify vehicle state")

    def snapshot(self) -> dict:
        return asdict(self)

    @classmethod
    def restore(cls, value: dict):
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
        ):
            raise ValueError("Invalid stored command context")
        if record.state == "pending":
            record.state = "uncertain"  # Never replay an interrupted mutation.
        return record
