from types import SimpleNamespace

from langchain.agents.middleware.types import ModelRequest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from agent_harness.context_assembler import (
    BudgetedContextMiddleware,
    ContextAssemblyConfig,
    ContextItem,
    ContextRuntime,
    ContextType,
)
from agent_harness.tools import BUILDER_TOOLS


def runtime() -> ContextRuntime:
    return ContextRuntime(
        request_id="r1",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={"environment": "dev", "approval_state": "approved"},
        context_items=[
            ContextItem(
                item_id="decision", content="Use the existing writer interface.",
                context_type=ContextType.WORKING_MEMORY, mandatory=True, relevance=1, priority=1,
            ),
            ContextItem(
                item_id="writer-test", content="Second writer call fails.",
                context_type=ContextType.EVIDENCE, relevance=1, priority=1,
            ),
        ],
        permitted_tool_names={"read_file", "run_tests"},
        config=ContextAssemblyConfig(
            model_context_limit=4000, application_operating_limit=4000,
            reserved_output_tokens=500, safety_margin_tokens=100,
        ),
    )


def test_middleware_injects_separated_context_and_filters_tools_without_another_call() -> None:
    state = runtime()
    model = FakeMessagesListChatModel(responses=[AIMessage(content="unused")])
    model_request = ModelRequest(
        model=model,
        messages=[HumanMessage(content="Add overwrite handling.")],
        tools=list(BUILDER_TOOLS),
        runtime=SimpleNamespace(context=state),
    )
    captured = []

    def handler(request: ModelRequest) -> AIMessage:
        captured.append(request)
        return AIMessage(content="one model call")

    response = BudgetedContextMiddleware().wrap_model_call(model_request, handler)
    assert response.content == "one model call"
    assert len(captured) == 1
    injected = captured[0].messages[-1].content
    assert "WORKING MEMORY" in injected and "[decision]" in injected
    assert "SELECTED EVIDENCE" in injected and "[writer-test]" in injected
    assert {tool.name for tool in captured[0].tools} == {"read_file", "run_tests"}
    assert state.manifest is not None
    assert "ContextManifest" not in injected
    assert "Second writer call fails." not in state.manifest.model_dump_json()
