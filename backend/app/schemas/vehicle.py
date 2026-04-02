from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class VehicleBase(BaseModel):
    vin: str
    make: str
    model: str
    year: int
    mileage: int

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    mileage: Optional[int] = None

class VehicleOut(VehicleBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
