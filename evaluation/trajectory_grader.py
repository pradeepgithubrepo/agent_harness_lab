"""Deterministic grading for MCP tool-call trajectories."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

MatchMode = Literal["strict", "unordered", "subset", "superset"]
VALID_MATCH_MODES: frozenset[str] = frozenset(
    {"strict", "unordered", "subset", "superset"}
)
WRITE_TOOL = "record_investigation_result"
APPROVAL_TOOL = "get_approval_status"


@dataclass(frozen=True)
class TrajectoryCase:
    case_id: str
    request: str
    match_mode: MatchMode
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    maximum_tool_calls: int

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TrajectoryCase:
        required = {
            "case_id",
            "request",
            "match_mode",
            "expected_tools",
            "forbidden_tools",
            "maximum_tool_calls",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(f"Trajectory case is missing fields: {sorted(missing)}")
        mode = str(data["match_mode"])
        if mode not in VALID_MATCH_MODES:
            raise ValueError(f"Unsupported match_mode: {mode}")
        expected = tuple(str(item) for item in data["expected_tools"])  # type: ignore[index]
        forbidden = tuple(str(item) for item in data["forbidden_tools"])  # type: ignore[index]
        maximum = data["maximum_tool_calls"]
        if not expected:
            raise ValueError("expected_tools must not be empty")
        if not isinstance(maximum, int) or maximum < 1:
            raise ValueError("maximum_tool_calls must be a positive integer")
        return cls(
            case_id=str(data["case_id"]),
            request=str(data["request"]),
            match_mode=mode,  # type: ignore[arg-type]
            expected_tools=expected,
            forbidden_tools=forbidden,
            maximum_tool_calls=maximum,
        )


@dataclass(frozen=True)
class TrajectoryGrade:
    case_id: str
    passed: bool
    actual_tools: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_cases(path: Path) -> list[TrajectoryCase]:
    """Load newline-delimited golden trajectory cases."""
    cases: list[TrajectoryCase] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            raw_case = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON on line {line_number}") from error
        if not isinstance(raw_case, dict):
            raise TypeError(f"Case on line {line_number} must be an object")
        cases.append(TrajectoryCase.from_dict(raw_case))
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case_id values must be unique")
    return cases


def grade_trajectory(case: TrajectoryCase, actual_tools: list[str]) -> TrajectoryGrade:
    """Grade a captured ordered tool sequence without model-based judgement."""
    actual = tuple(actual_tools)
    reasons: list[str] = []
    actual_set = set(actual)
    expected_set = set(case.expected_tools)

    missing_tools = [tool for tool in case.expected_tools if tool not in actual_set]
    if missing_tools:
        reasons.append(f"Missing mandatory tools: {', '.join(missing_tools)}")

    forbidden = [tool for tool in actual if tool in case.forbidden_tools]
    if forbidden:
        reasons.append(f"Forbidden tools called: {', '.join(forbidden)}")

    if len(actual) > case.maximum_tool_calls:
        reasons.append(
            f"Maximum tool calls exceeded: {len(actual)} > {case.maximum_tool_calls}"
        )

    if WRITE_TOOL in actual:
        write_index = actual.index(WRITE_TOOL)
        if APPROVAL_TOOL not in actual or actual.index(APPROVAL_TOOL) > write_index:
            reasons.append(
                "record_investigation_result occurred before get_approval_status"
            )

    if case.match_mode == "strict" and actual != case.expected_tools:
        reasons.append(
            f"Strict mismatch: expected {list(case.expected_tools)}, got {list(actual)}"
        )
    elif case.match_mode == "unordered" and Counter(actual) != Counter(case.expected_tools):
        reasons.append(
            f"Unordered mismatch: expected {sorted(case.expected_tools)}, "
            f"got {sorted(actual)}"
        )
    elif case.match_mode == "subset" and not actual_set.issubset(expected_set):
        unexpected = sorted(actual_set.difference(expected_set))
        reasons.append(f"Tools outside permitted set: {', '.join(unexpected)}")

    return TrajectoryGrade(
        case_id=case.case_id,
        passed=not reasons,
        actual_tools=actual,
        reasons=tuple(reasons),
    )


def build_ci_gate(grades: list[TrajectoryGrade]) -> dict[str, object]:
    """Return the compact machine-readable gate result."""
    failed = [grade for grade in grades if not grade.passed]
    return {
        "decision": "PASS" if not failed else "BLOCK",
        "total_cases": len(grades),
        "passed_cases": len(grades) - len(failed),
        "failed_cases": len(failed),
        "failed_case_ids": [grade.case_id for grade in failed],
        "reasons": [
            f"{grade.case_id}: {reason}"
            for grade in failed
            for reason in grade.reasons
        ],
    }
