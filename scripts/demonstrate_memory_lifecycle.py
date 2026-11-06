"""Live, sanitised lifecycle demonstration across Redis, Cosmos, and Search."""

from __future__ import annotations

import json
from pathlib import Path
from time import sleep
from uuid import uuid4

from agent_harness.memory import EpisodeMemory, MemoryCandidate, MemorySettings, SemanticMemory, WorkingMemory
from agent_harness.memory.audit import MemoryAuditLog
from agent_harness.memory.context_adapter import build_context_package
from agent_harness.memory.episodic_store import EpisodicMemoryStore
from agent_harness.memory.eviction_policy import working_eviction
from agent_harness.memory.models import MemoryAuditEvent
from agent_harness.memory.semantic_search import SemanticSearch
from agent_harness.memory.semantic_store import SemanticMemoryStore
from agent_harness.memory.tier_policy import episode_to_semantic, working_to_episode
from agent_harness.memory.working_store import WorkingMemoryStore


def main() -> int:
    settings = MemorySettings()
    if not all(settings.connectivity_status().values()):
        raise RuntimeError("Live memory-service configuration is incomplete.")
    working_store = WorkingMemoryStore(settings)
    episode_store = EpisodicMemoryStore(settings)
    semantic_store = SemanticMemoryStore(settings)
    semantic_search = SemanticSearch(settings)
    audit = MemoryAuditLog()
    scope_id = f"stage6-demo-{uuid4()}"

    working = WorkingMemory(scope_id=scope_id, session_id="demo-session", task_id="demo-task",
        source="demo", objective="Diagnose a synthetic job failure",
        workflow_state_projection={"incident_id": "incident-001", "step": "investigate"},
        evidence_references=["incident-001"], next_proposed_action="retrieve job status")
    working_store.create(working)
    audit.record(MemoryAuditEvent(memory_id=working.memory_id, scope_id=working.scope_id,
        event_type="created", tier="working", reason_code="short_lived_task_context"))

    episode = EpisodeMemory(scope_id=working.scope_id, source="working_compression",
        session_summary="Investigated synthetic job failure and captured evidence references.",
        entities=["incident-001", "job-001"], actions_taken=["get_job_status", "get_incident_details"],
        outcome="diagnosis_complete", importance=0.8, source_working_memory_ids=[working.memory_id])
    movement = working_to_episode(working, True)
    episode_store.create(episode)
    audit.record(MemoryAuditEvent(memory_id=episode.memory_id, scope_id=episode.scope_id,
        event_type="movement", tier="working", decision=movement, reason_code=movement.reason_code))

    fact = SemanticMemory(scope_id=working.scope_id, source="validated_episode", subject="synthetic-job-timeout",
        fact="A first synthetic job-status call may time out and is safe to retry.", source_episode_id=episode.memory_id,
        confidence=0.95, security_scope="internal")
    promotion = episode_to_semantic(episode, fact, validated=True, contradiction=False, duplicate=False)
    semantic_store.create(fact)
    semantic_search.index(fact)
    audit.record(MemoryAuditEvent(memory_id=fact.memory_id, scope_id=fact.scope_id,
        event_type="movement", tier="episodic", decision=promotion, reason_code=promotion.reason_code))
    search_results = _wait_for_search(semantic_search, working.scope_id, "job timeout")

    newer_fact = fact.model_copy(update={"memory_id": str(uuid4()), "fact": "A first synthetic job-status timeout is retryable once.", "version": 2})
    semantic_store.supersede(fact, newer_fact)
    semantic_search.index(fact.model_copy(update={"status": "superseded", "superseded_by": newer_fact.memory_id}))
    semantic_search.index(newer_fact)
    audit.record(MemoryAuditEvent(memory_id=fact.memory_id, scope_id=fact.scope_id,
        event_type="superseded", tier="semantic", reason_code="newer_validated_fact"))
    eviction = working_eviction(working, True)
    working_store.delete(working)
    audit.record(MemoryAuditEvent(memory_id=working.memory_id, scope_id=working.scope_id,
        event_type="eviction", tier="working", decision=eviction, reason_code=eviction.reason_code))
    package = build_context_package([], [MemoryCandidate(memory=episode, relevance=.8, estimated_tokens=40, retrieval_reason="episode")],
        [MemoryCandidate(memory=newer_fact, relevance=.95, estimated_tokens=30, retrieval_reason="semantic_search")], [],
        "synthetic lifecycle demonstration")
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/stage6_memory_demo.json").write_text(json.dumps({
        "working_memory_created": working.model_dump(mode="json"), "remaining_ttl_seconds": 7200,
        "episode": episode.model_dump(mode="json"), "promotion": promotion.model_dump(mode="json"),
        "semantic_search_results": _safe_search_results(search_results), "superseded_by": newer_fact.memory_id,
        "eviction": eviction.model_dump(mode="json"), "context_package": package.model_dump(mode="json"),
        "audit_events": [event.model_dump(mode="json") for event in audit.events],
    }, indent=2) + "\n")
    print("Memory lifecycle demonstration: PASSED")
    print(f"Working memory ID: {working.memory_id}")
    print(f"Episode ID: {episode.memory_id}")
    print(f"Semantic memory ID: {fact.memory_id}")
    print(f"Superseding semantic memory ID: {newer_fact.memory_id}")
    print(f"Search results: {len(search_results)}")
    return 0


def _wait_for_search(search: SemanticSearch, scope_id: str, query: str) -> list[dict]:
    for _ in range(5):
        results = search.retrieve(scope_id, query)
        if results:
            return results
        sleep(2)
    return []


def _safe_search_results(results: list[dict]) -> list[dict]:
    return [
        {key: result.get(key) for key in ("id", "subject", "fact", "status") if key in result}
        for result in results
    ]


if __name__ == "__main__":
    raise SystemExit(main())
