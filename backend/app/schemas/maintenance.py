from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class MaintenanceTaskOut(BaseModel):
    id: UUID
    code: str
    category: str
    titleEn: str
    titleAr: str
    intervalKm: Optional[int] = None
    intervalDays: Optional[int] = None
    dueInKm: Optional[int] = None
    dueInDays: Optional[int] = None
    status: str
    progress: int
    lastCompletedKm: int
    lastCompletedAt: Optional[datetime] = None


class MaintenanceCompleteRequest(BaseModel):
    notes: Optional[str] = None
