import pytest

from agent_harness.durable_orchestration.state import IncidentStage
from agent_harness.durable_orchestration.transitions import InvalidTransitionError, ensure_transition


def test_transition_rules_are_explicit() -> None:
    assert ensure_transition("RECEIVED", IncidentStage.TRIAGING) == "TRIAGING"
    with pytest.raises(InvalidTransitionError):
        ensure_transition("RECEIVED", IncidentStage.REMEDIATING)
