"""In-memory audit collector; callers decide where audit events are retained."""

from .models import MemoryAuditEvent


class MemoryAuditLog:
    def __init__(self) -> None:
        self.events: list[MemoryAuditEvent] = []

    def record(self, event: MemoryAuditEvent) -> None:
        self.events.append(event)
