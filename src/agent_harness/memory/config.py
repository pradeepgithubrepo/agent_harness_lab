"""Secret-safe Azure memory settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    azure_redis_host: str | None = None
    azure_redis_port: int = 6380
    azure_redis_access_key: SecretStr | None = None
    azure_redis_ssl: bool = True
    cosmos_endpoint: str | None = None
    cosmos_access_key: SecretStr | None = None
    cosmos_database: str = "agent_memory"
    cosmos_episodes_container: str = "episodes"
    cosmos_semantic_container: str = "semantic_facts"
    azure_search_endpoint: str | None = None
    azure_search_api_key: SecretStr | None = None
    azure_search_memory_index: str = "idx-agent-semantic-memory"
    working_memory_ttl_seconds: int = 7200
    episodic_memory_ttl_seconds: int = 7776000

    def connectivity_status(self) -> dict[str, bool]:
        return {
            "redis_configured": bool(self.azure_redis_host and self.azure_redis_access_key),
            "cosmos_configured": bool(self.cosmos_endpoint and self.cosmos_access_key),
            "search_configured": bool(self.azure_search_endpoint and self.azure_search_api_key),
        }
