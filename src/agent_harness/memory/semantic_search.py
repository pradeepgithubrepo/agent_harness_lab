"""Azure AI Search retrieval layer; Cosmos remains authoritative."""

from __future__ import annotations

from typing import Any

from .config import MemorySettings
from .models import SemanticMemory


class SemanticSearch:
    def __init__(self, settings: MemorySettings, client: Any | None = None) -> None:
        if client is None:
            if not settings.connectivity_status()["search_configured"]:
                raise RuntimeError("Azure AI Search memory configuration is incomplete.")
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
            assert settings.azure_search_api_key is not None
            client = SearchClient(
                endpoint=settings.azure_search_endpoint, index_name=settings.azure_search_memory_index,
                credential=AzureKeyCredential(settings.azure_search_api_key.get_secret_value()),
            )
        self.client = client

    def index(self, memory: SemanticMemory) -> None:
        self.client.upload_documents(documents=[{
            "id": memory.memory_id, "scope_id": memory.scope_id, "subject": memory.subject,
            "fact": memory.fact, "supporting_details": memory.supporting_details or "",
            "status": memory.status, "security_scope": memory.security_scope,
        }])

    def retrieve(self, scope_id: str, query: str, top: int = 5) -> list[dict[str, Any]]:
        return [dict(result) for result in self.client.search(
            search_text=query, filter=f"scope_id eq '{scope_id}' and status eq 'active'", top=top)]
