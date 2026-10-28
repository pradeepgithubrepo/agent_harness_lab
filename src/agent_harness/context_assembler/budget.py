"""Small, local token-budget policy. Counts are estimates, not provider exact."""

from __future__ import annotations

from math import ceil, floor

from .models import ContextAssemblyConfig


class ContextBudgetError(ValueError):
    """Raised for invalid budgets or mandatory context that cannot be admitted."""


def estimate_tokens(text: str, *, characters_per_token: int = 4) -> int:
    """Return a character-ratio token estimate for the Stage 1 policy."""
    if characters_per_token <= 0:
        raise ContextBudgetError("characters_per_token must be positive")
    return ceil(len(text) / characters_per_token) if text else 0


def calculate_budget(config: ContextAssemblyConfig) -> tuple[int, int, int]:
    effective = min(config.model_context_limit, config.application_operating_limit)
    available = effective - config.reserved_output_tokens - config.safety_margin_tokens
    if available < 0:
        raise ContextBudgetError(
            "reserved output tokens and safety margin exceed the effective context limit"
        )
    return effective, available, floor(available * config.maximum_input_utilisation)
