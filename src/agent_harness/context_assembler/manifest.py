"""Manifest construction kept separate from LangChain message mutation."""

from __future__ import annotations

from .models import ContextManifest


def build_manifest(
    *,
    request_id: str,
    agent_role: str,
    effective_context_limit: int,
    available_input_tokens: int,
    packing_limit: int,
    estimated_tokens_used: int,
    included_item_ids: tuple[str, ...],
    compacted_item_ids: tuple[str, ...],
    excluded_items: dict[str, str],
    selected_tool_names: tuple[str, ...],
    warnings: tuple[str, ...] = (),
) -> ContextManifest:
    return ContextManifest(
        request_id=request_id,
        agent_role=agent_role,
        effective_context_limit=effective_context_limit,
        available_input_tokens=available_input_tokens,
        packing_limit=packing_limit,
        estimated_tokens_used=estimated_tokens_used,
        remaining_tokens=packing_limit - estimated_tokens_used,
        included_item_ids=included_item_ids,
        compacted_item_ids=compacted_item_ids,
        excluded_items=excluded_items,
        selected_tool_names=selected_tool_names,
        warnings=warnings,
        policy_version="langchain-middleware-v1",
    )
