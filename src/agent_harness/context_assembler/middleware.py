"""LangChain model-call middleware with a small deterministic admission policy."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AnyMessage, SystemMessage

from .budget import ContextBudgetError, calculate_budget, estimate_tokens
from .manifest import build_manifest
from .models import (
    ContextAssemblyResult,
    ContextItem,
    ContextRuntime,
    ContextType,
)


class BudgetedContextMiddleware(AgentMiddleware):
    """Inject selected context and permitted structured tools before each model call."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        runtime = self._runtime(request)
        result = assemble_context(
            runtime,
            request.messages,
            request.tools or [],
            system_instruction=str(request.system_message.content)
            if request.system_message
            else "",
        )
        runtime.manifest = result.manifest
        injected = SystemMessage(content=_render_context(result.selected_items, runtime))
        return handler(
            request.override(
                messages=[*request.messages, injected],
                tools=[
                    tool
                    for tool in (request.tools or [])
                    if _tool_name(tool) in result.selected_tool_names
                ],
            )
        )

    @staticmethod
    def _runtime(request: ModelRequest) -> ContextRuntime:
        context = request.runtime.context if request.runtime else None
        if not isinstance(context, ContextRuntime):
            raise ContextBudgetError(
                "BudgetedContextMiddleware requires ContextRuntime as invocation context."
            )
        return context


def assemble_context(
    runtime: ContextRuntime,
    messages: Iterable[AnyMessage],
    tools: Iterable[Any],
    *,
    system_instruction: str = "",
) -> ContextAssemblyResult:
    """Apply the local policy without calling a model or external provider."""
    effective, available, packing_limit = calculate_budget(runtime.config)
    selected_tools = tuple(
        sorted(
            (
                tool
                for tool in tools
                if _tool_name(tool) in runtime.permitted_tool_names
            ),
            key=_tool_name,
        )
    )
    tool_tokens = sum(
        estimate_tokens(
            json.dumps(_tool_schema(tool), sort_keys=True),
            characters_per_token=runtime.config.characters_per_token,
        )
        for tool in selected_tools
    )
    protected_text = "\n".join([system_instruction, *_message_contents(messages)])
    protected_tokens = estimate_tokens(
        protected_text, characters_per_token=runtime.config.characters_per_token
    ) + tool_tokens
    if protected_tokens > packing_limit:
        raise ContextBudgetError("protected request state and permitted tool schemas exceed packing limit")

    selected: list[ContextItem] = []
    excluded: dict[str, str] = {}
    compacted: list[str] = []
    used = protected_tokens
    mandatory = [item for item in runtime.context_items if item.mandatory]
    optional = sorted(
        (item for item in runtime.context_items if not item.mandatory),
        key=lambda item: (
            -item.relevance,
            -item.priority,
            _item_tokens(item, runtime),
            item.item_id,
        ),
    )
    for item in mandatory:
        token_count = _item_tokens(item, runtime)
        if used + token_count > packing_limit:
            raise ContextBudgetError(f"mandatory context item {item.item_id} exceeds packing limit")
        selected.append(item)
        used += token_count

    for item in optional:
        full_tokens = _item_tokens(item, runtime)
        if used + full_tokens <= packing_limit:
            selected.append(item)
            used += full_tokens
            continue
        compact = item.compact_content
        if compact:
            compact_tokens = estimate_tokens(
                compact, characters_per_token=runtime.config.characters_per_token
            )
            if used + compact_tokens <= packing_limit:
                selected.append(
                    item.model_copy(
                        update={"content": compact, "estimated_tokens": compact_tokens}
                    )
                )
                compacted.append(item.item_id)
                used += compact_tokens
                continue
        excluded[item.item_id] = "CONTEXT_BUDGET_EXCEEDED"

    used = _request_tokens(
        runtime, messages, selected_tools, tuple(selected), system_instruction
    )
    while used > packing_limit:
        optional_selected = [item for item in selected if not item.mandatory]
        if not optional_selected:
            raise ContextBudgetError("mandatory context exceeds packing limit")
        evicted = optional_selected[-1]
        selected.remove(evicted)
        excluded[evicted.item_id] = "CONTEXT_BUDGET_EXCEEDED"
        used = _request_tokens(
            runtime, messages, selected_tools, tuple(selected), system_instruction
        )

    manifest = build_manifest(
        request_id=runtime.request_id,
        agent_role=runtime.agent_role,
        effective_context_limit=effective,
        available_input_tokens=available,
        packing_limit=packing_limit,
        estimated_tokens_used=used,
        included_item_ids=tuple(item.item_id for item in selected),
        compacted_item_ids=tuple(compacted),
        excluded_items=excluded,
        selected_tool_names=tuple(_tool_name(tool) for tool in selected_tools),
    )
    return ContextAssemblyResult(
        selected_items=tuple(selected),
        selected_tool_names=manifest.selected_tool_names,
        manifest=manifest,
    )


def _item_tokens(item: ContextItem, runtime: ContextRuntime) -> int:
    return item.estimated_tokens or estimate_tokens(
        item.content, characters_per_token=runtime.config.characters_per_token
    )


def _message_contents(messages: Iterable[AnyMessage]) -> list[str]:
    return [str(message.content) for message in messages]


def _request_tokens(
    runtime: ContextRuntime,
    messages: Iterable[AnyMessage],
    tools: Iterable[Any],
    items: tuple[ContextItem, ...],
    system_instruction: str,
) -> int:
    text = "\n".join([system_instruction, *_message_contents(messages), _render_context(items, runtime)])
    return estimate_tokens(
        text, characters_per_token=runtime.config.characters_per_token
    ) + sum(
        estimate_tokens(
            json.dumps(_tool_schema(tool), sort_keys=True),
            characters_per_token=runtime.config.characters_per_token,
        )
        for tool in tools
    )


def _render_context(items: tuple[ContextItem, ...], runtime: ContextRuntime) -> str:
    sections = {
        ContextType.RUNTIME_STATE: [],
        ContextType.WORKING_MEMORY: [],
        ContextType.EVIDENCE: [],
    }
    for item in items:
        sections[item.context_type].append(f"[{item.item_id}]\n{item.content}")
    return "\n\n".join(
        (
            "RUNTIME STATE\n"
            + json.dumps(
                {
                    **runtime.workflow_state,
                    "agent_role": runtime.agent_role,
                    "task_type": runtime.task_type,
                },
                sort_keys=True,
            )
            + _joined(sections[ContextType.RUNTIME_STATE]),
            "WORKING MEMORY\n" + _joined(sections[ContextType.WORKING_MEMORY]),
            "SELECTED EVIDENCE\n" + _joined(sections[ContextType.EVIDENCE]),
        )
    )


def _joined(items: list[str]) -> str:
    return ("\n" + "\n".join(items)) if items else ""


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name") or tool.get("function", {}).get("name", ""))
    return str(tool.name)


def _tool_schema(tool: Any) -> dict[str, Any]:
    if isinstance(tool, dict):
        return tool
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.args,
    }
