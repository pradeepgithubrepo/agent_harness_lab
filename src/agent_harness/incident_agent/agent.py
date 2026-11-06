from typing import Any

from langchain.agents import create_agent

from agent_harness.context_assembler.middleware import BudgetedContextMiddleware
from agent_harness.context_assembler.models import ContextRuntime
from agent_harness.incident_agent.mcp_tools import McpToolInvoker, create_mcp_tools

INCIDENT_RESOLUTION_INSTRUCTION = (
    "You investigate Databricks incidents using the supplied MCP tools. "
    "Never record an investigation result until approval status has been checked."
)


def create_incident_resolution_agent(
    model: Any,
    *,
    mcp_tool_invoker: McpToolInvoker | None = None,
) -> Any:
    """Create the sole model-backed incident agent with MCP-backed tools."""
    return create_agent(
        model=model,
        tools=create_mcp_tools(mcp_tool_invoker),
        system_prompt=INCIDENT_RESOLUTION_INSTRUCTION,
        middleware=[BudgetedContextMiddleware()],
        context_schema=ContextRuntime,
        name="incident_resolution",
    )
