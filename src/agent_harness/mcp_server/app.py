"""Official MCP SDK server; tools expose capabilities, never workflow routing."""
from __future__ import annotations
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from agent_harness.synthetic_databricks.models import SimulatedDatabricksTimeout
from .adapters.synthetic_backend import SyntheticBackend
from .schemas.job import JobStatusRequest, JobStatusResult
from .schemas.incident import IncidentDetailsRequest, IncidentDetailsResult
from .schemas.investigation import InvestigationRequest, InvestigationResult
from .schemas.approval import ApprovalStatusRequest, ApprovalStatusResult
from .schemas.common import utcnow
from .config import ApplicationSettings

def create_app(backend: SyntheticBackend | None = None) -> FastMCP:
    backend = backend or SyntheticBackend()
    app = FastMCP("Agent Harness Operations MCP Server", host="0.0.0.0", port=8000, streamable_http_path="/", stateless_http=True)
    @app.tool()
    def get_job_status(job_id: str, environment: str, correlation_id: str | None = None, workflow_id: str | None = None) -> dict:
        request = JobStatusRequest(job_id=job_id, environment=environment, correlation_id=correlation_id, workflow_id=workflow_id)
        try: status = backend.job_status(request.job_id)
        except SimulatedDatabricksTimeout: raise RuntimeError("SYNTHETIC_BACKEND_TIMEOUT")
        return JobStatusResult(job_id=request.job_id, environment=request.environment, status=status, checked_at=utcnow(), correlation_id=request.resolved_correlation_id(), source="synthetic").model_dump(mode="json")
    @app.tool()
    def get_incident_details(incident_id: str, correlation_id: str | None = None, workflow_id: str | None = None) -> dict:
        request=IncidentDetailsRequest(incident_id=incident_id, correlation_id=correlation_id, workflow_id=workflow_id); return IncidentDetailsResult(**backend.incident(request.incident_id), correlation_id=request.resolved_correlation_id()).model_dump(mode="json")
    @app.tool()
    def record_investigation_result(workflow_id: str, incident_id: str, classification: str, summary: str, recommended_action: str, evidence_references: list[str], correlation_id: str | None = None) -> dict:
        request=InvestigationRequest(workflow_id=workflow_id, incident_id=incident_id, classification=classification, summary=summary, recommended_action=recommended_action, evidence_references=evidence_references, correlation_id=correlation_id); return InvestigationResult(record_id=backend.record(request.model_dump()), workflow_id=request.workflow_id, incident_id=request.incident_id, persisted=True, recorded_at=utcnow(), correlation_id=request.resolved_correlation_id()).model_dump(mode="json")
    @app.tool()
    def get_approval_status(approval_id: str, approval_version: int, workflow_id: str | None = None, correlation_id: str | None = None) -> dict:
        request=ApprovalStatusRequest(approval_id=approval_id, approval_version=approval_version, workflow_id=workflow_id, correlation_id=correlation_id); return ApprovalStatusResult(**backend.approval(request.approval_id,request.approval_version), correlation_id=request.resolved_correlation_id()).model_dump(mode="json")
    return app


def create_asgi_app(settings: ApplicationSettings | None = None) -> Starlette:
    settings = settings or ApplicationSettings()
    settings.validate_selected_backend()
    mcp = create_app()

    async def live(_: object) -> JSONResponse:
        return JSONResponse({"status": "alive"})

    async def ready(_: object) -> JSONResponse:
        return JSONResponse({"status": "ready", "environment": settings.mcp_environment, "backend_mode": settings.mcp_backend_mode})

    mcp_app = mcp.streamable_http_app()
    @asynccontextmanager
    async def lifespan(_: Starlette):
        async with mcp.session_manager.run():
            yield
    return Starlette(lifespan=lifespan, routes=[
        Route("/health/live", live),
        Route("/health/ready", ready),
        Mount("/mcp", app=mcp_app),
    ])


if __name__ == "__main__":
    import uvicorn
    runtime_settings = ApplicationSettings()
    uvicorn.run(create_asgi_app(runtime_settings), host=runtime_settings.mcp_host, port=runtime_settings.mcp_port)
