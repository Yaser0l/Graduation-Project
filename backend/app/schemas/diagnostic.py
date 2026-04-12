from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class DiagnosticReportBase(BaseModel):
    vehicle_id: UUID
    dtc_codes: List[str]
    llm_explanation: Optional[str] = None
    urgency: str
    estimated_cost_min: Optional[int] = None
    estimated_cost_max: Optional[int] = None


class DiagnosticReportOut(DiagnosticReportBase):
    id: UUID
    resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    # Extended fields from JOINs
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None

    class Config:
        from_attributes = True


class FullReportRequest(BaseModel):
    language: Optional[str] = "en"
