from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from uuid import UUID
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserOut
from app.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

@router.get("/", response_model=List[VehicleOut])
async def get_vehicles(
    db: AsyncSession = Depends(get_db), current_user: UserOut = Depends(get_current_user)
):
    query = text("SELECT * FROM vehicles WHERE user_id = :user_id ORDER BY created_at DESC")
    result = await db.execute(query, {"user_id": current_user.id})
    return result.all()

@router.post("/", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_in: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    query = text(
        """
        INSERT INTO vehicles (user_id, vin, make, model, year, mileage) 
        VALUES (:user_id, :vin, :make, :model, :year, :mileage) 
        RETURNING *
        """
    )
    result = await db.execute(
        query,
        {
            "user_id": current_user.id,
            "vin": vehicle_in.vin,
            "make": vehicle_in.make,
            "model": vehicle_in.model,
            "year": vehicle_in.year,
            "mileage": vehicle_in.mileage
        }
    )
    vehicle = result.first()
    await db.commit()
    return vehicle

@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    query = text("SELECT * FROM vehicles WHERE id = :id AND user_id = :user_id")
    result = await db.execute(query, {"id": vehicle_id, "user_id": current_user.id})
    vehicle = result.first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: UUID,
    vehicle_in: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    if vehicle_in.mileage is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    if vehicle_in.mileage < 0:
        raise HTTPException(status_code=400, detail="Mileage cannot be negative")

    query = text(
        """
        UPDATE vehicles
        SET mileage = :mileage
        WHERE id = :id AND user_id = :user_id
        RETURNING *
        """
    )
    result = await db.execute(
        query,
        {
            "id": vehicle_id,
            "user_id": current_user.id,
            "mileage": vehicle_in.mileage,
        }
    )
    vehicle = result.first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    await db.commit()
    return vehicle
