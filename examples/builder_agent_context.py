"""Build a budget-safe context package for a Builder Agent."""

from context_engineering import (
    ContextAssembler,
    ContextCandidate,
    ContextCategory,
    TokenEstimator,
)


def candidate(
    candidate_id: str,
    category: ContextCategory,
    content: str,
    *,
    priority: int,
    mandatory: bool = False,
) -> ContextCandidate:
    return ContextCandidate.from_content(
        id=candidate_id,
        category=category,
        content=content,
        priority=priority,
        mandatory=mandatory,
        estimator=TokenEstimator(characters_per_token=10),
    )


def main() -> None:
    candidates = [
        candidate(
            "locked-operating-constraints",
            ContextCategory.WORKING_MEMORY,
            "Use only approved dependencies and do not change deployment configuration. "
            * 3,
            priority=100,
            mandatory=True,
        ),
        candidate(
            "controller-decision",
            ContextCategory.WORKING_MEMORY,
            "Implement the Writer capability and preserve the current public API. " * 2,
            priority=100,
            mandatory=True,
        ),
        candidate(
            "writer-implementation",
            ContextCategory.RETRIEVED_DOCUMENT,
            "class Writer: validate input, render output, and report actionable errors. "
            * 3,
            priority=90,
        ),
        candidate(
            "writer-tests",
            ContextCategory.RETRIEVED_DOCUMENT,
            "Tests cover success cases, invalid inputs, and output formatting. " * 2,
            priority=90,
        ),
        candidate(
            "output-contract",
            ContextCategory.TOOL_SCHEMA,
            "Writer output must include a status, content, and structured diagnostics. " * 2,
            priority=100,
            mandatory=True,
        ),
        candidate(
            "azure-devops-pipeline",
            ContextCategory.RETRIEVED_DOCUMENT,
            "Pipeline runs linting, unit tests, packaging, and deployment stages. " * 2,
            priority=10,
        ),
        candidate(
            "old-deployment-logs",
            ContextCategory.RETRIEVED_DOCUMENT,
            "Historical deployment log: an intermittent timeout occurred last quarter. " * 2,
            priority=5,
        ),
        candidate(
            "fabric-documentation",
            ContextCategory.RETRIEVED_DOCUMENT,
            "Fabric documentation describes workspace setup and unrelated governance topics. "
            * 2,
            priority=1,
        ),
    ]

    result = ContextAssembler(total_token_budget=100).assemble(candidates)
    print("Selected:", ", ".join(result.selected_candidate_ids))
    print("Excluded:", ", ".join(result.excluded_candidate_ids))
    print(f"Used: {result.used_tokens}; remaining: {result.remaining_tokens}")
    for candidate_id, reason in result.exclusion_reasons.items():
        print(f"- {candidate_id}: {reason}")


if __name__ == "__main__":
    main()
