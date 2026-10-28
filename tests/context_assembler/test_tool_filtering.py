from langchain_core.messages import HumanMessage

from agent_harness.context_assembler import (
    ContextAssemblyConfig,
    ContextRuntime,
    assemble_context,
)
from agent_harness.tools import BUILDER_TOOLS


def test_only_permitted_complete_tool_schemas_are_admitted() -> None:
    runtime = ContextRuntime(
        request_id="r",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={},
        context_items=[],
        permitted_tool_names={"read_file", "search_code", "edit_file", "run_tests"},
        config=ContextAssemblyConfig(
            model_context_limit=4000, application_operating_limit=4000,
            reserved_output_tokens=500, safety_margin_tokens=100,
        ),
    )
    result = assemble_context(runtime, [HumanMessage(content="change writer")], BUILDER_TOOLS)
    assert result.selected_tool_names == ("edit_file", "read_file", "run_tests", "search_code")
    assert "trigger_pipeline" not in result.selected_tool_names
    assert result.manifest.estimated_tokens_used > 0
