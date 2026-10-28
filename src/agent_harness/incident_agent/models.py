from pydantic import BaseModel


class SyntheticDiagnosis(BaseModel):
    summary: str
    proposed_action: str
