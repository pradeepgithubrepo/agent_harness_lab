from __future__ import annotations

import pytest

from context_engineering import (
    ContextAssembler,
    ContextCandidate,
    ContextCategory,
    MandatoryContextOverflowError,
    TokenEstimator,
)


def candidate(
    candidate_id: str,
    tokens: int,
    *,
    priority: int = 0,
    mandatory: bool = False,
) -> ContextCandidate:
    return ContextCandidate(
        id=candidate_id,
        category=ContextCategory.RETRIEVED_DOCUMENT,
        content=f"context for {candidate_id}",
        token_estimate=tokens,
        priority=priority,
        mandatory=mandatory,
    )


def test_normal_allocation_selects_mandatory_then_highest_priority_that_fits() -> None:
    result = ContextAssembler(total_token_budget=10).assemble(
        [
            candidate("required", 3, mandatory=True),
            candidate("low", 2, priority=1),
            candidate("high", 4, priority=10),
        ]
    )

    assert result.selected_candidate_ids == ("required", "high", "low")
    assert result.excluded_candidate_ids == ()
    assert result.used_tokens == 9
    assert result.remaining_tokens == 1


def test_mandatory_context_overflow_raises_clear_error() -> None:
    with pytest.raises(
        MandatoryContextOverflowError,
        match=r"requires 7 tokens, exceeding the budget of 5.*alpha, beta",
    ):
        ContextAssembler(total_token_budget=5).assemble(
            [
                candidate("beta", 3, mandatory=True),
                candidate("alpha", 4, mandatory=True),
            ]
        )


def test_optional_candidate_is_excluded_when_it_does_not_fit() -> None:
    result = ContextAssembler(total_token_budget=5).assemble(
        [
            candidate("required", 3, mandatory=True),
            candidate("too-large", 3, priority=10),
            candidate("fits", 2, priority=1),
        ]
    )

    assert result.selected_candidate_ids == ("required", "fits")
    assert result.excluded_candidate_ids == ("too-large",)
    assert result.exclusion_reasons == {
        "too-large": "does_not_fit_remaining_budget (needs 3, has 2)"
    }


def test_exact_budget_usage_is_allowed() -> None:
    result = ContextAssembler(total_token_budget=8).assemble(
        [
            candidate("required", 3, mandatory=True),
            candidate("optional", 5, priority=1),
        ]
    )

    assert result.selected_candidate_ids == ("required", "optional")
    assert result.used_tokens == 8
    assert result.remaining_tokens == 0


def test_ordering_is_deterministic_for_mandatory_and_equal_priority_candidates() -> None:
    candidates = [
        candidate("z-required", 1, mandatory=True),
        candidate("beta", 1, priority=5),
        candidate("alpha", 1, priority=5),
        candidate("a-required", 1, mandatory=True),
    ]

    first = ContextAssembler(total_token_budget=4).assemble(candidates)
    second = ContextAssembler(total_token_budget=4).assemble(reversed(candidates))

    assert first.selected_candidate_ids == ("a-required", "z-required", "alpha", "beta")
    assert second == first


def test_character_based_estimator_is_configurable() -> None:
    estimator = TokenEstimator(characters_per_token=3)
    context = ContextCandidate.from_content(
        id="estimated",
        category=ContextCategory.WORKING_MEMORY,
        content="abcdefgh",
        estimator=estimator,
    )

    assert context.token_estimate == 3
