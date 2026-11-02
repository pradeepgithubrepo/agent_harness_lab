"""Explicit movement policy; confidence alone never promotes semantic memory."""

from .models import EpisodeMemory, SemanticMemory, TierMovementDecision, WorkingMemory


def working_to_episode(working: WorkingMemory, task_completed: bool) -> TierMovementDecision:
    useful = task_completed and bool(working.objective or working.evidence_references)
    return TierMovementDecision(
        source_tier="working", target_tier="episodic",
        action="compress_to_episode" if useful else "retain",
        reason_code="meaningful_task_completed" if useful else "task_not_completed_or_empty",
        confidence=1.0 if useful else 0.5, validation_required=False, approved=useful,
    )


def episode_to_semantic(
    episode: EpisodeMemory, candidate: SemanticMemory, validated: bool, contradiction: bool, duplicate: bool
) -> TierMovementDecision:
    approved = validated and not contradiction and not duplicate and candidate.confidence >= 0.85
    return TierMovementDecision(
        source_tier="episodic", target_tier="semantic",
        action="promote_to_semantic" if approved else "reject",
        reason_code=(
            "validated_reusable_knowledge" if approved else
            "validation_required" if not validated else
            "unresolved_contradiction" if contradiction else
            "duplicate_active_fact" if duplicate else "insufficient_confidence"
        ),
        confidence=candidate.confidence, validation_required=True, approved=approved,
    )
