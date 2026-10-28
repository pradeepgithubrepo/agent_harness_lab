from pydantic_settings import BaseSettings, SettingsConfigDict


class McpClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mcp_server_url: str = "https://ca-agent-harness-mcp-dev.greenstone-965acf9a.centralindia.azurecontainerapps.io/mcp/"
    mcp_connect_timeout_seconds: int = 5
    mcp_request_timeout_seconds: int = 30
