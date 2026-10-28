from datetime import datetime
from pydantic import Field
from .common import StrictModel, ToolRequest

class IncidentDetailsRequest(ToolRequest):
    incident_id: str = Field(min_length=1, max_length=80)
class IncidentDetailsResult(StrictModel):
    incident_id: str; job_id: str; category: str; description: str; created_at: datetime; current_status: str; correlation_id: str
