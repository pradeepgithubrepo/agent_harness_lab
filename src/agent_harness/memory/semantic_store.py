"""Cosmos DB authoritative, versioned semantic-memory store."""

from __future__ import annotations

from typing import Any

from .config import MemorySettings
from .models import SemanticMemory


class SemanticMemoryStore:
    def __init__(self, settings: MemorySettings, container: Any | None = None) -> None:
        if container is None:
            if not settings.connectivity_status()["cosmos_configured"]:
                raise RuntimeError("Cosmos semantic-memory configuration is incomplete.")
            from azure.cosmos import CosmosClient
            assert settings.cosmos_access_key is not None
            database = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_access_key.get_secret_value()).get_database_client(settings.cosmos_database)
            container = database.get_container_client(settings.cosmos_semantic_container)
        self.container = container

    def create(self, memory: SemanticMemory) -> None:
        body = memory.model_dump(mode="json")
        body["id"] = memory.memory_id
        self.container.create_item(body)

    def active_by_subject(self, scope_id: str, subject: str) -> list[SemanticMemory]:
        query = "SELECT * FROM c WHERE c.scope_id = @scope AND c.subject = @subject AND c.status = 'active'"
        return [SemanticMemory.model_validate(_record(item)) for item in self.container.query_items(
            query=query, parameters=[{"name": "@scope", "value": scope_id}, {"name": "@subject", "value": subject}],
            partition_key=scope_id)]

    def update(self, memory: SemanticMemory) -> None:
        body = memory.model_dump(mode="json")
        body["id"] = memory.memory_id
        self.container.replace_item(memory.memory_id, body)

    def supersede(self, old: SemanticMemory, replacement: SemanticMemory) -> None:
        self.update(old.model_copy(update={"status": "superseded", "superseded_by": replacement.memory_id, "version": old.version + 1}))
        self.create(replacement)


def _record(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in {"id", "_etag", "_rid", "_self", "_attachments", "_ts"}}
