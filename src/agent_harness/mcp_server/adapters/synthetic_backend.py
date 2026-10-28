from __future__ import annotations
from agent_harness.synthetic_databricks import SyntheticDatabricksClient
from ..schemas.approval import ApprovalStatus
from ..schemas.common import utcnow

class SyntheticBackend:
    def __init__(self, client: SyntheticDatabricksClient | None = None) -> None:
        self.client = client or SyntheticDatabricksClient()
        self.investigations: dict[str, dict] = {}
    def job_status(self, job_id: str) -> str:
        return self.client.get_job_status(job_id).status
    def incident(self, incident_id: str) -> dict:
        return {"incident_id": incident_id, "job_id": "daily_sales_refresh", "category": "DATA_FRESHNESS", "description": "gold_daily_sales is stale", "created_at": utcnow(), "current_status": "OPEN"}
    def record(self, data: dict) -> str:
        record_id=f"investigation:{len(self.investigations)+1}"; self.investigations[record_id]=data; return record_id
    def approval(self, approval_id: str, version: int) -> dict:
        now=utcnow(); return {"approval_id":approval_id,"approval_version":version,"status":ApprovalStatus.PENDING,"requested_at":now,"deadline":now,"evaluated_at":now}
