from langchain_core.messages import HumanMessage

from agent_harness.context_assembler import (
    ContextAssemblyConfig,
    ContextItem,
    ContextRuntime,
    ContextType,
    assemble_context,
)


def runtime(items: list[ContextItem]) -> ContextRuntime:
    return ContextRuntime(
        request_id="r",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={},
        context_items=items,
        permitted_tool_names=set(),
        config=ContextAssemblyConfig(
            model_context_limit=400,
            application_operating_limit=400,
            reserved_output_tokens=50,
            safety_margin_tokens=50,
            maximum_input_utilisation=0.85,
        ),
    )


def test_optional_sorting_is_deterministic_and_manifest_is_metadata_only() -> None:
    items = [
        ContextItem(item_id="z", content="z", context_type=ContextType.EVIDENCE, relevance=1, priority=1),
        ContextItem(item_id="a", content="a", context_type=ContextType.EVIDENCE, relevance=1, priority=1),
    ]
    first = assemble_context(runtime(items), [HumanMessage(content="request")], [])
    second = assemble_context(runtime(list(reversed(items))), [HumanMessage(content="request")], [])
    assert first.manifest.included_item_ids == ("a", "z")
    assert first.manifest == second.manifest
    assert '"content"' not in first.manifest.model_dump_json()


def test_approved_compact_content_is_used_and_full_content_is_never_truncated() -> None:
    item = ContextItem(
        item_id="compact",
        content="x" * 1400,
        compact_content="approved compact evidence",
        context_type=ContextType.EVIDENCE,
        relevance=1,
        priority=1,
    )
    result = assemble_context(runtime([item]), [HumanMessage(content="request")], [])
    selected = result.selected_items[0]
    assert selected.content == "approved compact evidence"
    assert result.manifest.compacted_item_ids == ("compact",)
