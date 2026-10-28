"""Thin Streamable HTTP client; it contains no retry or LangGraph logic."""
from __future__ import annotations
import json
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from .config import McpClientSettings
from .errors import McpConnectionError, McpDiscoveryError, McpToolExecutionError, McpToolNotFoundError, McpToolTimeoutError


class McpOperationsClient:
    def __init__(self, settings: McpClientSettings | None = None) -> None:
        self.settings = settings or McpClientSettings()
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self._tools: set[str] = set()

    async def __aenter__(self) -> "McpOperationsClient":
        try:
            read, write, _ = await self._stack.enter_async_context(
                streamablehttp_client(self.settings.mcp_server_url, timeout=self.settings.mcp_request_timeout_seconds)
            )
            self._session = await self._stack.enter_async_context(ClientSession(read, write))
            await self._session.initialize()
        except Exception as error:
            await self._stack.aclose()
            raise McpConnectionError("Unable to connect to MCP server") from error
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._stack.aclose()

    async def list_tools(self) -> list[dict]:
        if not self._session: raise McpConnectionError("MCP session is not connected")
        try:
            response = await self._session.list_tools()
            self._tools = {tool.name for tool in response.tools}
            return [{"name": tool.name, "input_schema": tool.inputSchema} for tool in response.tools]
        except Exception as error:
            raise McpDiscoveryError("Unable to discover MCP tools") from error

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        if not self._session: raise McpConnectionError("MCP session is not connected")
        if self._tools and tool_name not in self._tools:
            raise McpToolNotFoundError(f"Unknown MCP tool: {tool_name}")
        try:
            result = await self._session.call_tool(tool_name, arguments)
        except TimeoutError as error:
            raise McpToolTimeoutError("MCP tool request timed out") from error
        except Exception as error:
            raise McpToolExecutionError("MCP tool execution failed") from error
        if result.isError:
            text = " ".join(getattr(item, "text", "") for item in result.content)
            if "TIMEOUT" in text:
                raise McpToolTimeoutError("The job-status backend timed out")
            raise McpToolExecutionError("MCP tool returned a controlled error")
        if result.structuredContent is not None:
            return dict(result.structuredContent)
        text = "".join(getattr(item, "text", "") for item in result.content)
        return json.loads(text)
