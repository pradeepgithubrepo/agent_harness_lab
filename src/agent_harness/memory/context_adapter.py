"""Candidate-only adapter; the Context Assembler owns final prompt inclusion."""

from .models import MemoryCandidate, MemoryContextPackage


def build_context_package(
    working: list[MemoryCandidate],
    episodic: list[MemoryCandidate],
    semantic: list[MemoryCandidate],
    excluded: list[MemoryCandidate],
    retrieval_reason: str,
) -> MemoryContextPackage:
    candidates = [*working, *episodic, *semantic]
    return MemoryContextPackage(
        working_memory=working, episodic_memories=episodic, semantic_memories=semantic,
        excluded_memories=excluded, retrieval_reason=retrieval_reason,
        total_candidate_tokens=sum(candidate.estimated_tokens for candidate in candidates),
    )
