from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID

class VehicleBase(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17, description="Vehicle Identification Number")
    make: str
    model: str
    year: int
    mileage: int
    oil_program_km: int = Field(default=10000, ge=5000, le=10000)

class VehicleCreate(VehicleBase):
    initialize_maintenance_baseline: bool = True
    last_service_km: Optional[int] = Field(default=None, ge=0)
    last_service_date: Optional[date] = None

class VehicleUpdate(BaseModel):
    mileage: Optional[int] = None

class VehicleOut(VehicleBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
