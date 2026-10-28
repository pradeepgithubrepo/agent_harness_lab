"""Centralized, safe MCP settings. Tools never read environment variables."""
from __future__ import annotations

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mcp_environment: str = "local"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_transport: str = "streamable-http"
    mcp_log_level: str = "INFO"
    mcp_auth_mode: str = "development"
    mcp_backend_mode: str = "synthetic"
    mcp_allowed_tools: str = "get_job_status,get_incident_details,record_investigation_result,get_approval_status"
    databricks_client_id: str | None = None
    databricks_client_secret: SecretStr | None = None
    databricks_host: str | None = None
    databricks_auth_type: str | None = None
    agent_ado_enabled: bool = False
    agent_ado_auth_mode: str | None = None
    agent_ado_tenant_id: str | None = None
    agent_ado_client_id: str | None = None
    agent_ado_client_secret: SecretStr | None = None
    agent_ado_organization: str | None = None
    agent_ado_project: str | None = None
    agent_ado_ci_pipeline_id: str | None = None

    @field_validator("mcp_backend_mode")
    @classmethod
    def backend_mode(cls, value: str) -> str:
        if value not in {"synthetic", "databricks"}:
            raise ValueError("MCP_BACKEND_MODE must be synthetic or databricks")
        return value

    def validate_selected_backend(self) -> None:
        if self.mcp_backend_mode == "databricks":
            missing = [name for name, value in {
                "DATABRICKS_CLIENT_ID": self.databricks_client_id,
                "DATABRICKS_CLIENT_SECRET": self.databricks_client_secret,
                "DATABRICKS_HOST": self.databricks_host,
            }.items() if not value]
            if missing:
                raise ValueError("Missing required configuration: " + ", ".join(missing))

    def safe_summary(self) -> dict[str, object]:
        return {"environment": self.mcp_environment, "backend_mode": self.mcp_backend_mode, "authentication_mode": self.mcp_auth_mode, "databricks_configured": bool(self.databricks_host and self.databricks_client_id and self.databricks_client_secret), "ado_enabled": self.agent_ado_enabled, "allowed_tools": self.mcp_allowed_tools.split(","), "host": self.mcp_host, "port": self.mcp_port}
