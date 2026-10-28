from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from agent_harness.agents import create_builder_agent
from agent_harness.context_assembler import ContextAssemblyConfig, ContextRuntime


def test_builder_agent_instantiates_with_a_fake_model_without_credentials() -> None:
    agent = create_builder_agent(FakeMessagesListChatModel(responses=[AIMessage(content="ok")]))
    assert agent is not None


def test_builder_agent_runs_with_fake_model_and_runtime_context() -> None:
    runtime = ContextRuntime(
        request_id="r",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={},
        context_items=[],
        permitted_tool_names=set(),
        config=ContextAssemblyConfig(
            model_context_limit=4000,
            application_operating_limit=4000,
            reserved_output_tokens=500,
            safety_margin_tokens=100,
        ),
    )
    agent = create_builder_agent(FakeMessagesListChatModel(responses=[AIMessage(content="ok")]))
    result = agent.invoke({"messages": [{"role": "user", "content": "hello"}]}, context=runtime)
    assert result["messages"][-1].content == "ok"
    assert runtime.manifest is not None
