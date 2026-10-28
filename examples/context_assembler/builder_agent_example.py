"""Run the LangChain middleware policy with a fake local model-call handler."""

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


def item(
    item_id: str,
    content: str,
    context_type: ContextType,
    *,
    mandatory: bool = False,
    relevance: float = 1,
    priority: int = 1,
) -> ContextItem:
    return ContextItem(
        item_id=item_id,
        content=content,
        context_type=context_type,
        mandatory=mandatory,
        relevance=relevance,
        priority=priority,
    )


def main() -> None:
    user_request = "Add overwrite handling to the writer and update the relevant tests."
    runtime = ContextRuntime(
        request_id="builder-overwrite",
        agent_role="Builder",
        task_type="code_change",
        workflow_state={
            "environment": "dev",
            "controller_decision": "Implement overwrite behind the existing Writer interface.",
            "attempt": 1,
        },
        context_items=[
            item("engineering-constraints", "Preserve public APIs and do not deploy.", ContextType.RUNTIME_STATE, mandatory=True),
            item("output-instructions", "Return changed files and test results.", ContextType.RUNTIME_STATE, mandatory=True),
            item("latest-failure", "A second writer call fails when a destination exists.", ContextType.WORKING_MEMORY, relevance=1, priority=8),
            item("writer-interface", "Writer.write accepts destination and options.", ContextType.EVIDENCE, relevance=1, priority=7),
            item("writer-implementation", "Persistence currently rejects an existing destination.", ContextType.EVIDENCE, relevance=0.9, priority=6),
            item("writer-tests", "Tests cover initial write behavior.", ContextType.EVIDENCE, relevance=0.9, priority=5),
            item("repository-readme", "General repository setup documentation.", ContextType.EVIDENCE, relevance=0.1),
            item("old-deployment-log", "Historical deployment timeout.", ContextType.EVIDENCE, relevance=0.1),
            item("fabric-guide", "Fabric guidance outside the writer task.", ContextType.EVIDENCE, relevance=0),
        ],
        permitted_tool_names={"read_file", "search_code", "edit_file", "run_tests"},
        config=ContextAssemblyConfig(
            model_context_limit=740,
            application_operating_limit=740,
            reserved_output_tokens=250,
            safety_margin_tokens=100,
        ),
    )
    request = ModelRequest(
        model=FakeMessagesListChatModel(responses=[AIMessage(content="unused")]),
        messages=[HumanMessage(content=user_request)],
        tools=list(BUILDER_TOOLS),
        runtime=SimpleNamespace(context=runtime),
    )
    captured: list[ModelRequest] = []
    BudgetedContextMiddleware().wrap_model_call(
        request,
        lambda updated: captured.append(updated) or AIMessage(content="demo model response"),
    )
    updated = captured[0]
    manifest = runtime.manifest
    assert manifest is not None

    print("Original user request:", user_request)
    print("Mandatory context injected:", [item_id for item_id in manifest.included_item_ids if item_id in {"engineering-constraints", "output-instructions"}])
    print("Optional context admitted:", [item_id for item_id in manifest.included_item_ids if item_id not in {"engineering-constraints", "output-instructions"}])
    print("Optional context excluded:", manifest.excluded_items)
    print("Tools exposed to model:", [tool.name for tool in updated.tools])
    print("Tools excluded:", ["trigger_pipeline"])
    print("Estimated input tokens:", manifest.estimated_tokens_used)
    print("Remaining packing capacity:", manifest.remaining_tokens)
    print("\nLANGCHAIN MODEL MESSAGES")
    for message in updated.messages:
        print(f"{message.type.upper()}: {message.content}")
    print("\nMETADATA-ONLY MANIFEST")
    print(manifest.model_dump_json())


if __name__ == "__main__":
    main()
