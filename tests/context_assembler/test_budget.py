import pytest

from agent_harness.context_assembler import (
    ContextAssemblyConfig,
    ContextBudgetError,
    ContextItem,
    ContextRuntime,
    ContextType,
    assemble_context,
    calculate_budget,
)
from langchain_core.messages import HumanMessage


def config(**updates: object) -> ContextAssemblyConfig:
    values = {
        "model_context_limit": 1000,
        "application_operating_limit": 800,
        "reserved_output_tokens": 100,
        "safety_margin_tokens": 50,
    }
    values.update(updates)
    return ContextAssemblyConfig(
        **values,
    )


def runtime(items: list[ContextItem], **updates: object) -> ContextRuntime:
    return ContextRuntime(
        request_id="r1",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={"environment": "dev"},
        context_items=items,
        permitted_tool_names=set(),
        config=config(**updates),
    )


def test_effective_limit_and_packing_limit_are_protected() -> None:
    assert calculate_budget(config()) == (800, 650, 552)


def test_invalid_reservations_raise_typed_error() -> None:
    with pytest.raises(ContextBudgetError):
        calculate_budget(config(reserved_output_tokens=790, safety_margin_tokens=20))


def test_mandatory_overflow_raises_and_optional_context_stays_within_limit() -> None:
    mandatory = ContextItem(
        item_id="must", content="x" * 3000, context_type=ContextType.WORKING_MEMORY,
        mandatory=True, relevance=1, priority=1,
    )
    with pytest.raises(ContextBudgetError):
        assemble_context(runtime([mandatory]), [HumanMessage(content="request")], [])

    optional = ContextItem(
        item_id="optional", content="useful evidence", context_type=ContextType.EVIDENCE,
        relevance=1, priority=1,
    )
    result = assemble_context(runtime([optional]), [HumanMessage(content="request")], [])
    assert result.manifest.estimated_tokens_used <= result.manifest.packing_limit
