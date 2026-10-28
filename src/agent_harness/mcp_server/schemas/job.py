from datetime import datetime
from enum import StrEnum
from pydantic import Field
from .common import StrictModel, ToolRequest

class Environment(StrEnum):
    LOCAL = "local"
    DEV = "dev"
class JobStatus(StrEnum):
    PENDING="PENDING"; RUNNING="RUNNING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"
class JobStatusRequest(ToolRequest):
    job_id: str = Field(min_length=1, max_length=80)
    environment: Environment
class JobStatusResult(StrictModel):
    job_id: str; environment: Environment; status: JobStatus; checked_at: datetime; correlation_id: str; source: str
