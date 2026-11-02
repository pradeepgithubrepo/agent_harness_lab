"""Thin lifecycle coordinator; it never owns workflow state or checkpoints."""

from .audit import MemoryAuditLog
from .episodic_store import EpisodicMemoryStore
from .models import EpisodeMemory, MemoryAuditEvent, SemanticMemory, WorkingMemory
from .semantic_search import SemanticSearch
from .semantic_store import SemanticMemoryStore
from .tier_policy import episode_to_semantic, working_to_episode
from .working_store import WorkingMemoryStore


class MemoryManager:
    def __init__(self, working: WorkingMemoryStore, episodes: EpisodicMemoryStore,
                 semantic: SemanticMemoryStore, search: SemanticSearch, audit: MemoryAuditLog) -> None:
        self.working, self.episodes, self.semantic, self.search, self.audit = working, episodes, semantic, search, audit

    def complete_working(self, working: WorkingMemory, episode: EpisodeMemory) -> None:
        decision = working_to_episode(working, task_completed=True)
        self.audit.record(MemoryAuditEvent(memory_id=working.memory_id, scope_id=working.scope_id,
            event_type="movement", tier="working", decision=decision, reason_code=decision.reason_code))
        if decision.approved:
            self.episodes.create(episode)

    def promote(self, episode: EpisodeMemory, fact: SemanticMemory, validated: bool) -> bool:
        duplicate = bool(self.semantic.active_by_subject(fact.scope_id, fact.subject))
        decision = episode_to_semantic(episode, fact, validated, contradiction=False, duplicate=duplicate)
        self.audit.record(MemoryAuditEvent(memory_id=fact.memory_id, scope_id=fact.scope_id,
            event_type="movement", tier="episodic", decision=decision, reason_code=decision.reason_code))
        if not decision.approved:
            return False
        self.semantic.create(fact)
        self.search.index(fact)
        return True
