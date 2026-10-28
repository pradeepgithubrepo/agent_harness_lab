from typing import Any

from agent_harness.agents import create_builder_agent


def create_incident_resolution_agent(model: Any) -> Any:
    """The sole model-backed agent used by the durable incident workflow."""
    return create_builder_agent(model)
