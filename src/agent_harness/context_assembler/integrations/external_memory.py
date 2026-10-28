"""Future external-memory boundary; intentionally inactive in the MVP."""

from __future__ import annotations

from ..models import ContextItem


class ExternalMemoryProvider:
    def retrieve(self, query: str, limit: int) -> list[ContextItem]:
        raise NotImplementedError("External memory retrieval is not implemented in this MVP.")
