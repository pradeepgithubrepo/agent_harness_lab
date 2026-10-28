from datetime import datetime
from enum import StrEnum
from pydantic import Field
from .common import StrictModel, ToolRequest

class Classification(StrEnum):
    TRANSIENT_FAILURE="TRANSIENT_FAILURE"; CONFIGURATION_ERROR="CONFIGURATION_ERROR"; APPLICATION_ERROR="APPLICATION_ERROR"; EXTERNAL_DEPENDENCY_FAILURE="EXTERNAL_DEPENDENCY_FAILURE"; UNKNOWN="UNKNOWN"
class InvestigationRequest(ToolRequest):
    workflow_id: str = Field(min_length=1, max_length=80)
    incident_id: str = Field(min_length=1, max_length=80)
    classification: Classification
    summary: str = Field(min_length=1, max_length=1000)
    recommended_action: str = Field(min_length=1, max_length=500)
    evidence_references: list[str] = Field(max_length=20)
class InvestigationResult(StrictModel):
    record_id: str; workflow_id: str; incident_id: str; persisted: bool; recorded_at: datetime; correlation_id: str
