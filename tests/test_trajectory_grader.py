from evaluation.trajectory_grader import (
    TrajectoryCase,
    TrajectoryGrade,
    build_ci_gate,
    grade_trajectory,
)


def case(
    *,
    mode: str = "strict",
    expected: tuple[str, ...] = ("get_incident_details",),
    forbidden: tuple[str, ...] = (),
    maximum: int = 4,
) -> TrajectoryCase:
    return TrajectoryCase(
        case_id="TRAJ-TEST",
        request="test",
        match_mode=mode,  # type: ignore[arg-type]
        expected_tools=expected,
        forbidden_tools=forbidden,
        maximum_tool_calls=maximum,
    )


def test_strict_trajectory_passes_in_exact_order() -> None:
    result = grade_trajectory(
        case(expected=("get_incident_details", "get_job_status")),
        ["get_incident_details", "get_job_status"],
    )
    assert result.passed


def test_strict_trajectory_fails_when_order_changes() -> None:
    result = grade_trajectory(
        case(expected=("get_incident_details", "get_job_status")),
        ["get_job_status", "get_incident_details"],
    )
    assert not result.passed
    assert any("Strict mismatch" in reason for reason in result.reasons)


def test_unordered_match_passes_when_tools_are_reordered() -> None:
    result = grade_trajectory(
        case(
            mode="unordered",
            expected=("get_incident_details", "get_job_status"),
        ),
        ["get_job_status", "get_incident_details"],
    )
    assert result.passed


def test_missing_mandatory_tool_fails() -> None:
    result = grade_trajectory(
        case(expected=("get_incident_details", "get_job_status")),
        ["get_incident_details"],
    )
    assert not result.passed
    assert "Missing mandatory tools: get_job_status" in result.reasons


def test_forbidden_tool_fails() -> None:
    result = grade_trajectory(
        case(forbidden=("record_investigation_result",)),
        ["get_incident_details", "record_investigation_result"],
    )
    assert not result.passed
    assert "Forbidden tools called: record_investigation_result" in result.reasons


def test_recording_requires_prior_approval() -> None:
    result = grade_trajectory(
        case(
            expected=("record_investigation_result",),
            maximum=1,
        ),
        ["record_investigation_result"],
    )
    assert not result.passed
    assert (
        "record_investigation_result occurred before get_approval_status"
        in result.reasons
    )


def test_ci_gate_reports_pass_and_block_decisions() -> None:
    passing = TrajectoryGrade(
        case_id="TRAJ-PASS",
        passed=True,
        actual_tools=("get_incident_details",),
        reasons=(),
    )
    failing = TrajectoryGrade(
        case_id="TRAJ-BLOCK",
        passed=False,
        actual_tools=(),
        reasons=("Missing mandatory tools: get_job_status",),
    )

    assert build_ci_gate([passing]) == {
        "decision": "PASS",
        "total_cases": 1,
        "passed_cases": 1,
        "failed_cases": 0,
        "failed_case_ids": [],
        "reasons": [],
    }
    blocked = build_ci_gate([passing, failing])
    assert blocked["decision"] == "BLOCK"
    assert blocked["failed_case_ids"] == ["TRAJ-BLOCK"]
