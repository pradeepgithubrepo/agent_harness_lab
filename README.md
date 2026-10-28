# agent-harness-lab

## Databricks Incident Resolution Agent

This project contains one synthetic Databricks Incident Resolution Agent.

Stage 1 is LangChain `BudgetedContextMiddleware`: it admits mandatory context,
bounded working memory/evidence, and permitted tools before model calls.

Stage 2 is LangGraph durable orchestration: a checkpointed incident state
machine receives, investigates, diagnoses, waits for approval, remediates,
verifies, and resolves an incident.

The five durable concepts are: state machine, workflow state, checkpoint,
human-in-the-loop approval gate, and durable resume. The workflow retries the
first synthetic API timeout, uses a three-day logical approval deadline, tracks
four logical hours of activity, and uses a remediation idempotency key.

## Purpose

This repository demonstrates a small application policy for final context
admission before a model call. It protects mandatory request state, admits
caller-supplied working memory and evidence within a conservative estimated
input budget, filters tools by role policy, and records the decision in a
metadata-only manifest.

## Why LangChain middleware

LangChain owns the agent loop, messages, structured tools, model calls, and
model-call middleware lifecycle. `BudgetedContextMiddleware` runs immediately
before every model call and only supplies application policy LangChain cannot
infer: budget calculation, mandatory-context protection, optional admission,
role-based tool filtering, and a manifest.

## Runtime flow

```text
User request → LangChain agent → BudgetedContextMiddleware → model call
```

The middleware receives `ContextRuntime` through LangChain invocation context.
It preserves the existing user message, injects selected context as a system
message with `RUNTIME STATE`, `WORKING MEMORY`, and `SELECTED EVIDENCE`
sections, and supplies only permitted tool objects to the model.

## Model boundary

Sent to the model:
- LangChain `HumanMessage` user request;
- injected system context;
- complete LangChain tool schemas for permitted tools.

Outside the model:
- tool implementations, credentials, and permission grants;
- the metadata-only `ContextManifest`;
- external-memory and MCP providers.

The manifest never contains raw context, prompts, tool results, or secrets.

## Running the Builder example

```bash
python examples/context_assembler/builder_agent_example.py
python examples/durable_orchestration/run_incident.py
```

It uses a fake handler only—no provider credentials or network access—and
prints the final LangChain messages, exposed tool names, excluded context, and
manifest.

## Running tests

```bash
pytest
```

## MVP limitations and future extensions

V1 uses a configurable character-to-token estimate, a deterministic
relevance/priority ordering, and caller-supplied context only. It does not
perform retrieval, semantic ranking, LLM compression, or exact provider token
counting.

Future extension boundaries are external memory, MCP tool discovery,
model-aware token counting, Microsoft Foundry model adapters, and a later
LangGraph durable-orchestration layer for checkpoints, HITL, pause/resume, and
conditional workflows. This Stage 1 implementation adds no LangGraph
application code.

## Setup

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Test

```bash
pytest
```

## Examples

```bash
python examples/context_assembler/builder_initial_context.py
python examples/context_assembler/builder_iterative_context.py
```
