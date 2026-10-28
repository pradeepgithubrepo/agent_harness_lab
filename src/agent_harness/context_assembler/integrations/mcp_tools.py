"""Future external-tool discovery boundary; intentionally inactive in the MVP."""

from __future__ import annotations

from typing import Any


class ExternalToolProvider:
    def get_tools(self, agent_role: str, task_type: str) -> list[Any]:
        raise NotImplementedError("External or MCP tool discovery is not implemented in this MVP.")
