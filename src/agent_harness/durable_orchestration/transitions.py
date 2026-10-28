from .state import IncidentStage


class InvalidTransitionError(ValueError):
    pass


_ALLOWED = {
    IncidentStage.RECEIVED: {IncidentStage.TRIAGING},
    IncidentStage.TRIAGING: {IncidentStage.INVESTIGATING},
    IncidentStage.INVESTIGATING: {IncidentStage.DIAGNOSIS_READY, IncidentStage.FAILED},
    IncidentStage.DIAGNOSIS_READY: {IncidentStage.AWAITING_APPROVAL},
    IncidentStage.AWAITING_APPROVAL: {
        IncidentStage.REMEDIATING, IncidentStage.REJECTED,
        IncidentStage.INVESTIGATING, IncidentStage.ESCALATED,
    },
    IncidentStage.REMEDIATING: {IncidentStage.VERIFYING},
    IncidentStage.VERIFYING: {IncidentStage.RESOLVED, IncidentStage.INVESTIGATING, IncidentStage.FAILED},
}


def ensure_transition(current: str, target: IncidentStage) -> str:
    source = IncidentStage(current)
    if target not in _ALLOWED.get(source, set()):
        raise InvalidTransitionError(f"{source} cannot transition to {target}")
    return target.value
