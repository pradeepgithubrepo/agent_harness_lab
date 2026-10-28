# ADR 002: LangGraph durable incident orchestration

## Decision

Use one Databricks Incident Resolution Agent. LangChain owns messages, tools,
model calls, and `BudgetedContextMiddleware`. LangGraph owns the durable
incident state machine, SQLite checkpoints, approval interrupt/resume, retries,
and legal transitions.

## Rationale

The Stage 2 scenario needs recovery after a process restart, durable approval
waiting, and idempotent remediation. A logical clock makes three-day approval
tests immediate. Synthetic Databricks activities provide deterministic timeout,
rerun, and validation behavior.

Workflow state stores artifact references rather than complete evidence or
prompts. Real Databricks integration is deferred to a later MCP stage.
Temporal is not used for this MVP.
