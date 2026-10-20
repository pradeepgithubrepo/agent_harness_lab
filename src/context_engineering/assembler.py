"""Deterministic, budget-safe context allocation."""

from __future__ import annotations

from collections.abc import Iterable

from .models import AssemblyResult, ContextCandidate


class MandatoryContextOverflowError(ValueError):
    """Raised when required context cannot fit within the supplied budget."""


class ContextAssembler:
    """Select complete context candidates without exceeding a token budget."""

    def __init__(self, total_token_budget: int) -> None:
        if total_token_budget < 0:
            raise ValueError("total_token_budget must be greater than or equal to zero")
        self.total_token_budget = total_token_budget

    def assemble(self, candidates: Iterable[ContextCandidate]) -> AssemblyResult:
        """Allocate mandatory context, then optional context by priority and ID."""
        candidate_list = list(candidates)
        self._validate_unique_ids(candidate_list)

        mandatory = sorted(
            (candidate for candidate in candidate_list if candidate.mandatory),
            key=lambda candidate: candidate.id,
        )
        mandatory_tokens = sum(candidate.token_estimate for candidate in mandatory)
        if mandatory_tokens > self.total_token_budget:
            mandatory_ids = ", ".join(candidate.id for candidate in mandatory)
            raise MandatoryContextOverflowError(
                "Mandatory context requires "
                f"{mandatory_tokens} tokens, exceeding the budget of "
                f"{self.total_token_budget} tokens. Candidates: {mandatory_ids}"
            )

        selected_ids = [candidate.id for candidate in mandatory]
        remaining_tokens = self.total_token_budget - mandatory_tokens
        exclusions: dict[str, str] = {}

        optional = sorted(
            (candidate for candidate in candidate_list if not candidate.mandatory),
            key=lambda candidate: (-candidate.priority, candidate.id),
        )
        for candidate in optional:
            if candidate.token_estimate <= remaining_tokens:
                selected_ids.append(candidate.id)
                remaining_tokens -= candidate.token_estimate
            else:
                exclusions[candidate.id] = (
                    "does_not_fit_remaining_budget"
                    f" (needs {candidate.token_estimate}, has {remaining_tokens})"
                )

        return AssemblyResult(
            selected_candidate_ids=tuple(selected_ids),
            excluded_candidate_ids=tuple(exclusions),
            used_tokens=self.total_token_budget - remaining_tokens,
            remaining_tokens=remaining_tokens,
            exclusion_reasons=exclusions,
        )

    @staticmethod
    def _validate_unique_ids(candidates: list[ContextCandidate]) -> None:
        ids = [candidate.id for candidate in candidates]
        duplicate_ids = sorted(
            candidate_id for candidate_id in set(ids) if ids.count(candidate_id) > 1
        )
        if duplicate_ids:
            raise ValueError(
                "Context candidate IDs must be unique: " + ", ".join(duplicate_ids)
            )
