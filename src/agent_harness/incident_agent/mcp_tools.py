"""LangChain tools backed by the existing MCP operations client."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Protocol

from langchain_core.tools import StructuredTool

from agent_harness.mcp_client import McpOperationsClient


class McpToolInvoker(Protocol):
    """Synchronous boundary used by LangChain tool functions."""

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one MCP operation."""


class McpOperationsToolInvoker:
    """Invoke the existing Streamable HTTP client from synchronous tools."""

    def __init__(self, client_factory: Callable[[], McpOperationsClient] = McpOperationsClient) -> None:
        self._client_factory = client_factory

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self._call(tool_name, arguments))

    async def _call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with self._client_factory() as client:
            await client.list_tools()
            return await client.call_tool(tool_name, arguments)


def create_mcp_tools(invoker: McpToolInvoker | None = None) -> list[StructuredTool]:
    """Return the four production MCP operation tools for the incident agent."""

    caller = invoker or McpOperationsToolInvoker()

    def get_job_status(
        job_id: str,
        environment: str,
        correlation_id: str | None = None,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        """Get the current status of a Databricks job."""
        return caller.call(
            "get_job_status",
            {
                "job_id": job_id,
                "environment": environment,
                "correlation_id": correlation_id,
                "workflow_id": workflow_id,
            },
        )

    def get_incident_details(
        incident_id: str,
        correlation_id: str | None = None,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        """Get incident details and its affected job."""
        return caller.call(
            "get_incident_details",
            {
                "incident_id": incident_id,
                "correlation_id": correlation_id,
                "workflow_id": workflow_id,
            },
        )

    def get_approval_status(
        approval_id: str,
        approval_version: int,
        workflow_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Get the current approval state before recording an investigation."""
        return caller.call(
            "get_approval_status",
            {
                "approval_id": approval_id,
                "approval_version": approval_version,
                "workflow_id": workflow_id,
                "correlation_id": correlation_id,
            },
        )

    def record_investigation_result(
        workflow_id: str,
        incident_id: str,
        classification: str,
        summary: str,
        recommended_action: str,
        evidence_references: list[str],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an approved investigation result."""
        return caller.call(
            "record_investigation_result",
            {
                "workflow_id": workflow_id,
                "incident_id": incident_id,
                "classification": classification,
                "summary": summary,
                "recommended_action": recommended_action,
                "evidence_references": evidence_references,
                "correlation_id": correlation_id,
            },
        )

    functions = (
        get_job_status,
        get_incident_details,
        get_approval_status,
        record_investigation_result,
    )
    return [
        StructuredTool.from_function(function, name=function.__name__)
        for function in functions
    ]
