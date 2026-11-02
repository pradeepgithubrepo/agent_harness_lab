from __future__ import annotations

import json

from agent_harness.memory.config import MemorySettings
from agent_harness.memory.context_adapter import build_context_package
from agent_harness.memory.episodic_store import EpisodicMemoryStore
from agent_harness.memory.models import EpisodeMemory, MemoryCandidate, SemanticMemory, WorkingMemory
from agent_harness.memory.semantic_store import SemanticMemoryStore
from agent_harness.memory.tier_policy import episode_to_semantic
from agent_harness.memory.working_store import WorkingMemoryStore


class FakeRedis:
    def __init__(self): self.data, self.ttls = {}, {}
    def set(self, key, value, ex): self.data[key], self.ttls[key] = value, ex
    def get(self, key): return self.data.get(key)
    def keys(self, pattern): return list(self.data)
    def mget(self, keys): return [self.data.get(key) for key in keys]
    def delete(self, key): self.data.pop(key, None)
    def ttl(self, key): return self.ttls.get(key, -2)


class FakeContainer:
    def __init__(self): self.items = {}
    def create_item(self, item): self.items[item["id"]] = item
    def read_item(self, key, partition_key): return self.items[key]
    def replace_item(self, key, item): self.items[key] = item
    def delete_item(self, key, partition_key): self.items.pop(key)
    def query_items(self, **kwargs): return self.items.values()


def settings() -> MemorySettings:
    return MemorySettings()


def working() -> WorkingMemory:
    return WorkingMemory(scope_id="scope", session_id="session", task_id="task", source="test", objective="objective")


def episode() -> EpisodeMemory:
    return EpisodeMemory(scope_id="scope", source="test", session_summary="summary", outcome="done", importance=.8)


def semantic(source_episode_id: str) -> SemanticMemory:
    return SemanticMemory(scope_id="scope", source="test", subject="subject", fact="fact",
        source_episode_id=source_episode_id, confidence=.9, security_scope="internal")


def test_redis_crud_and_ttl() -> None:
    store = WorkingMemoryStore(settings(), FakeRedis())
    memory = working()
    store.create(memory)
    assert store.get("scope", "session", "task").memory_id == memory.memory_id
    assert store.ttl(memory) == 7200
    store.delete(memory)
    assert store.get("scope", "session", "task") is None


def test_episode_write_read_and_semantic_supersession() -> None:
    episode_store = EpisodicMemoryStore(settings(), FakeContainer())
    item = episode()
    episode_store.create(item)
    assert episode_store.read("scope", item.memory_id).outcome == "done"
    semantic_store = SemanticMemoryStore(settings(), FakeContainer())
    old, newer = semantic(item.memory_id), semantic(item.memory_id)
    semantic_store.create(old)
    semantic_store.supersede(old, newer)
    assert semantic_store.container.items[old.memory_id]["status"] == "superseded"


def test_unvalidated_promotion_is_rejected_and_duplicate_is_detected() -> None:
    item, fact = episode(), semantic("episode")
    decision = episode_to_semantic(item, fact, validated=False, contradiction=False, duplicate=False)
    assert decision.action == "reject"
    duplicate = episode_to_semantic(item, fact, validated=True, contradiction=False, duplicate=True)
    assert duplicate.reason_code == "duplicate_active_fact"


def test_context_package_and_secret_free_settings_summary() -> None:
    candidate = MemoryCandidate(memory=working(), relevance=.8, estimated_tokens=12, retrieval_reason="test")
    package = build_context_package([candidate], [], [], [], "test")
    assert package.total_candidate_tokens == 12
    assert set(settings().connectivity_status()) == {"redis_configured", "cosmos_configured", "search_configured"}
