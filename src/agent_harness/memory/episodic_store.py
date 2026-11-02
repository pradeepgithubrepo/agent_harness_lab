"""Cosmos DB authoritative episodic-memory store."""

from __future__ import annotations

from typing import Any

from .config import MemorySettings
from .models import EpisodeMemory


class EpisodicMemoryStore:
    def __init__(self, settings: MemorySettings, container: Any | None = None) -> None:
        if container is None:
            if not settings.connectivity_status()["cosmos_configured"]:
                raise RuntimeError("Cosmos episodic-memory configuration is incomplete.")
            from azure.cosmos import CosmosClient
            assert settings.cosmos_access_key is not None
            database = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_access_key.get_secret_value()).get_database_client(settings.cosmos_database)
            container = database.get_container_client(settings.cosmos_episodes_container)
        self.container = container
        self.ttl_seconds = settings.episodic_memory_ttl_seconds

    def create(self, memory: EpisodeMemory) -> None:
        body = memory.model_dump(mode="json")
        body.update({"id": memory.memory_id, "ttl": self.ttl_seconds})
        self.container.create_item(body)

    def read(self, scope_id: str, memory_id: str) -> EpisodeMemory:
        return EpisodeMemory.model_validate(_record(self.container.read_item(memory_id, partition_key=scope_id)))

    def list_by_scope(self, scope_id: str) -> list[EpisodeMemory]:
        return [EpisodeMemory.model_validate(_record(item)) for item in self.container.query_items(
            query="SELECT * FROM c WHERE c.scope_id = @scope", parameters=[{"name": "@scope", "value": scope_id}],
            partition_key=scope_id)]

    def search(self, scope_id: str, entity: str) -> list[EpisodeMemory]:
        return [item for item in self.list_by_scope(scope_id) if entity.lower() in {value.lower() for value in item.entities}]

    def update(self, memory: EpisodeMemory) -> None:
        body = memory.model_dump(mode="json")
        body.update({"id": memory.memory_id, "ttl": self.ttl_seconds})
        self.container.replace_item(memory.memory_id, body)

    def delete(self, scope_id: str, memory_id: str) -> None:
        self.container.delete_item(memory_id, partition_key=scope_id)


def _record(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in {"id", "ttl", "_etag", "_rid", "_self", "_attachments", "_ts"}}
