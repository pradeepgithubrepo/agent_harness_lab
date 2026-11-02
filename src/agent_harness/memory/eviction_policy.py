"""Auditable tier-specific eviction decisions."""

from .models import EpisodeMemory, EvictionDecision, SemanticMemory, WorkingMemory


def working_eviction(memory: WorkingMemory, task_completed: bool) -> EvictionDecision:
    return EvictionDecision(memory_id=memory.memory_id, tier="working",
        action="delete" if task_completed else "keep",
        reason_code="task_completed" if task_completed else "active_task")


def episodic_eviction(memory: EpisodeMemory) -> EvictionDecision:
    action = "archive" if memory.importance >= 0.7 or memory.failures_and_recoveries else "expire"
    return EvictionDecision(memory_id=memory.memory_id, tier="episodic", action=action,
        reason_code="retain_failure_or_important_episode" if action == "archive" else "routine_low_value_episode")


def semantic_eviction(memory: SemanticMemory, policy_removal: bool = False) -> EvictionDecision:
    action = "delete" if policy_removal else "supersede" if memory.superseded_by else "keep"
    return EvictionDecision(memory_id=memory.memory_id, tier="semantic", action=action,
        reason_code="policy_or_sensitivity_removal" if policy_removal else "newer_validated_fact" if memory.superseded_by else "active_validated_fact")
