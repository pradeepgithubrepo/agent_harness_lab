"""Redis-backed, non-authoritative short-lived working memory."""

from __future__ import annotations

import json
from typing import Any

from .config import MemorySettings
from .models import WorkingMemory


class WorkingMemoryStore:
    def __init__(self, settings: MemorySettings, client: Any | None = None) -> None:
        self.settings = settings
        if client is None:
            if not settings.connectivity_status()["redis_configured"]:
                raise RuntimeError("Redis memory configuration is incomplete.")
            import redis
            assert settings.azure_redis_access_key is not None
            client = redis.RedisCluster(
                host=settings.azure_redis_host, port=settings.azure_redis_port,
                password=settings.azure_redis_access_key.get_secret_value(),
                ssl=settings.azure_redis_ssl, decode_responses=True,
                address_remap=lambda _address: (settings.azure_redis_host, settings.azure_redis_port),
            )
        self.client = client

    @staticmethod
    def key(memory: WorkingMemory) -> str:
        return f"working:{memory.scope_id}:{memory.session_id}:{memory.task_id}"

    def create(self, memory: WorkingMemory) -> None:
        self.client.set(self.key(memory), json.dumps(memory.model_dump(mode="json")), ex=self.settings.working_memory_ttl_seconds)

    def get(self, scope_id: str, session_id: str, task_id: str) -> WorkingMemory | None:
        value = self.client.get(f"working:{scope_id}:{session_id}:{task_id}")
        return WorkingMemory.model_validate(json.loads(value)) if value else None

    def update(self, memory: WorkingMemory) -> None:
        self.create(memory.model_copy(update={"updated_at": memory.updated_at}))

    def list_by_scope(self, scope_id: str, session_id: str) -> list[WorkingMemory]:
        pattern = f"working:{scope_id}:{session_id}:*"
        keys = list(self.client.scan_iter(match=pattern)) if hasattr(self.client, "scan_iter") else self.client.keys(pattern)
        values = [self.client.get(key) for key in keys]
        return [WorkingMemory.model_validate(json.loads(value)) for value in values if value]

    def delete(self, memory: WorkingMemory) -> None:
        self.client.delete(self.key(memory))

    def ttl(self, memory: WorkingMemory) -> int:
        return int(self.client.ttl(self.key(memory)))
