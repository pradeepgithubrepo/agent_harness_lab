"""Execute and grade deterministic MCP tool trajectories for the CI gate."""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Self

import uvicorn
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from agent_harness.context_assembler import ContextAssemblyConfig, ContextRuntime
from agent_harness.incident_agent import create_incident_resolution_agent
from agent_harness.incident_agent.mcp_tools import McpOperationsToolInvoker, McpToolInvoker
from agent_harness.mcp_client import McpClientSettings, McpOperationsClient
from agent_harness.mcp_client.errors import (
    McpConnectionError,
    McpDiscoveryError,
    McpToolExecutionError,
    McpToolNotFoundError,
    McpToolTimeoutError,
)
from agent_harness.mcp_server.adapters.synthetic_backend import SyntheticBackend
from agent_harness.mcp_server.app import create_asgi_app

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.trajectory_grader import (
    TrajectoryCase,
    TrajectoryGrade,
    build_ci_gate,
    grade_trajectory,
    load_cases,
)

CASES_PATH = ROOT / "evaluation" / "tool_trajectory_cases.jsonl"
RESULTS_PATH = ROOT / "artifacts" / "trajectory_eval_results.json"
GATE_PATH = ROOT / "artifacts" / "ci_gate_result.json"
ALL_MCP_TOOLS = {
    "get_job_status",
    "get_incident_details",
    "get_approval_status",
    "record_investigation_result",
}


class RecordingMcpToolInvoker:
    """Capture ordered calls while delegating to the production MCP client path."""

    def __init__(self, delegate: McpToolInvoker) -> None:
        self.delegate = delegate
        self.tool_names: list[str] = []

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.tool_names.append(tool_name)
        try:
            return self.delegate.call(tool_name, arguments)
        except (
            McpConnectionError,
            McpDiscoveryError,
            McpToolExecutionError,
            McpToolNotFoundError,
            McpToolTimeoutError,
        ) as error:
            # This gate grades trajectories, not tool-result correctness. Preserve the
            # observed attempt as a synthetic tool response so a deterministic model
            # can complete the configured sequence.
            return {"synthetic_tool_error": type(error).__name__}


class ToolCallingFakeModel(FakeMessagesListChatModel):
    """Test model that accepts LangChain tool binding and returns scripted calls."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> ToolCallingFakeModel:
        return self


class LocalMcpServer:
    """Run the unmodified ASGI MCP app against a synthetic backend."""

    def __init__(self) -> None:
        backend = SyntheticBackend()
        backend.client.status_attempts = 1
        self.backend = backend
        self.port = _unused_port()
        self.server = uvicorn.Server(
            uvicorn.Config(create_asgi_app(), host="127.0.0.1", port=self.port, log_level="error")
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp/"

    def __enter__(self) -> Self:
        self.thread.start()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/health/ready", timeout=0.2
                ) as response:
                    if response.status == 200:
                        return self
            except OSError:
                time.sleep(0.05)
        self.server.should_exit = True
        self.thread.join(timeout=2)
        raise RuntimeError("Local synthetic MCP server did not become ready")

    def __exit__(self, *_: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def main() -> int:
    cases = load_cases(CASES_PATH)
    grades: list[TrajectoryGrade] = []
    with LocalMcpServer() as server:
        for case in cases:
            try:
                actual_tools = _execute_case(case, server.endpoint)
                grades.append(grade_trajectory(case, actual_tools))
            except Exception as error:  # noqa: BLE001 - each case must produce a gate result.
                grades.append(
                    TrajectoryGrade(
                        case_id=case.case_id,
                        passed=False,
                        actual_tools=(),
                        reasons=(f"Execution failed: {type(error).__name__}",),
                    )
                )

    gate = build_ci_gate(grades)
    _write_artifacts(cases, grades, gate)
    print(
        f"Trajectory evaluations: {gate['passed_cases']}/{gate['total_cases']} passed "
        f"({gate['decision']})"
    )
    return 0 if gate["decision"] == "PASS" else 1


def _execute_case(case: TrajectoryCase, endpoint: str) -> list[str]:
    settings = McpClientSettings(mcp_server_url=endpoint)
    invoker = RecordingMcpToolInvoker(
        McpOperationsToolInvoker(lambda: McpOperationsClient(settings))
    )
    agent = create_incident_resolution_agent(
        _scripted_model(case.case_id),
        mcp_tool_invoker=invoker,
    )
    agent.invoke(
        {"messages": [{"role": "user", "content": case.request}]},
        context=ContextRuntime(
            request_id=case.case_id,
            agent_role="IncidentResolver",
            task_type="trajectory_evaluation",
            workflow_state={"case_id": case.case_id, "environment": "dev"},
            context_items=[],
            permitted_tool_names=ALL_MCP_TOOLS,
            config=ContextAssemblyConfig(
                model_context_limit=8_000,
                application_operating_limit=8_000,
                reserved_output_tokens=500,
                safety_margin_tokens=100,
            ),
        ),
    )
    return invoker.tool_names


def _scripted_model(case_id: str) -> ToolCallingFakeModel:
    calls = _SCRIPTED_CALLS[case_id]
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": name, "args": arguments, "id": f"{case_id}-{index}"}
            ],
        )
        for index, (name, arguments) in enumerate(calls, start=1)
    ]
    responses.append(AIMessage(content="Synthetic trajectory complete."))
    return ToolCallingFakeModel(responses=responses)


_COMMON = {"workflow_id": "wf-1042", "incident_id": "INC-1042"}
_SCRIPTED_CALLS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    "TRAJ-001": [
        ("get_job_status", {"job_id": "daily_sales_refresh", "environment": "dev"}),
    ],
    "TRAJ-002": [
        ("get_incident_details", {"incident_id": "INC-1042"}),
    ],
    "TRAJ-003": [
        ("get_incident_details", {"incident_id": "INC-1042"}),
        ("get_job_status", {"job_id": "daily_sales_refresh", "environment": "dev"}),
    ],
    "TRAJ-004": [
        ("get_incident_details", {"incident_id": "INC-1042"}),
        ("get_job_status", {"job_id": "daily_sales_refresh", "environment": "dev"}),
        (
            "get_approval_status",
            {"approval_id": "AP-1042", "approval_version": 1, "workflow_id": "wf-1042"},
        ),
        (
            "record_investigation_result",
            {
                **_COMMON,
                "classification": "APPLICATION_ERROR",
                "summary": "Synthetic investigation completed.",
                "recommended_action": "Request remediation.",
                "evidence_references": ["evidence:failed-task-summary:v1"],
            },
        ),
    ],
    "TRAJ-005": [
        (
            "get_approval_status",
            {"approval_id": "AP-1042", "approval_version": 1, "workflow_id": "wf-1042"},
        ),
        (
            "record_investigation_result",
            {
                **_COMMON,
                "classification": "APPLICATION_ERROR",
                "summary": "Approval was checked before this synthetic write.",
                "recommended_action": "Request remediation.",
                "evidence_references": [],
            },
        ),
    ],
    "TRAJ-006": [
        ("get_incident_details", {"incident_id": "INC-1042"}),
    ],
}


def _write_artifacts(
    cases: list[TrajectoryCase],
    grades: list[TrajectoryGrade],
    gate: dict[str, object],
) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    by_id = {case.case_id: case for case in cases}
    results = [
        {
            "case_id": grade.case_id,
            "request": by_id[grade.case_id].request,
            "match_mode": by_id[grade.case_id].match_mode,
            "expected_tools": list(by_id[grade.case_id].expected_tools),
            **grade.to_dict(),
        }
        for grade in grades
    ]
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
    GATE_PATH.write_text(json.dumps(gate, indent=2) + "\n")


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


if __name__ == "__main__":
    sys.exit(main())
