"""Minimal LangChain Builder agent with injectable model dependency."""

from typing import Any

from langchain.agents import create_agent

from agent_harness.context_assembler.middleware import BudgetedContextMiddleware
from agent_harness.context_assembler.models import ContextRuntime
from agent_harness.tools import BUILDER_TOOLS


BUILDER_INSTRUCTION = (
    "You are a Builder agent. Make focused code changes, verify with tests, "
    "and do not deploy or trigger pipelines."
)


def create_builder_agent(model: Any) -> Any:
    """Create a credential-free-testable LangChain agent; model is caller supplied."""
    return create_agent(
        model=model,
        tools=BUILDER_TOOLS,
        system_prompt=BUILDER_INSTRUCTION,
        middleware=[BudgetedContextMiddleware()],
        context_schema=ContextRuntime,
        name="builder",
    )
