from datetime import datetime
from enum import StrEnum
from pydantic import Field
from .common import StrictModel, ToolRequest

class ApprovalStatus(StrEnum):
    PENDING="PENDING"; APPROVED="APPROVED"; REJECTED="REJECTED"; EXPIRED="EXPIRED"
class ApprovalStatusRequest(ToolRequest):
    approval_id: str = Field(min_length=1, max_length=100)
    approval_version: int = Field(gt=0)
class ApprovalStatusResult(StrictModel):
    approval_id: str; approval_version: int; status: ApprovalStatus; requested_at: datetime; deadline: datetime; evaluated_at: datetime; correlation_id: str
