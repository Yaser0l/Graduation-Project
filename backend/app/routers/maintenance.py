from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth import UserOut
from app.schemas.maintenance import MaintenanceTaskOut, MaintenanceCompleteRequest
from app.services.notify import notify_maintenance_alerts


router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("/vehicle/{vehicle_id}", response_model=List[MaintenanceTaskOut])
async def list_vehicle_maintenance(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    vehicle_query = text(
        """
        SELECT id, user_id, vin, make, model, year, mileage, oil_program_km, created_at
        FROM vehicles
        WHERE id = :vehicle_id AND user_id = :user_id
        """
    )
    vehicle_result = await db.execute(vehicle_query, {"vehicle_id": vehicle_id, "user_id": current_user.id})
    vehicle = vehicle_result.first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    now = datetime.now(timezone.utc)
    vehicle_mileage = int(vehicle.mileage or 0)
    oil_program_km = 5000 if int(vehicle.oil_program_km or 10000) == 5000 else 10000
    fallback_completed_at = vehicle.created_at if vehicle.created_at else now

    query = text(
        """
        SELECT
            mt.id,
            mt.code,
            mt.title_en,
            mt.title_ar,
            mt.category,
            mt.interval_km,
            mt.interval_days,
            mt.alert_window_km,
            mt.alert_window_days,
            vms.last_completed_km,
            vms.last_completed_at
        FROM maintenance_tasks mt
        LEFT JOIN vehicle_maintenance_state vms
            ON vms.task_id = mt.id AND vms.vehicle_id = :vehicle_id
        WHERE mt.is_active = TRUE
        ORDER BY mt.category, mt.title_en
        """
    )
    rows = (await db.execute(query, {"vehicle_id": vehicle_id})).all()

    items: List[MaintenanceTaskOut] = []
    alert_candidates = []
    for row in rows:
        interval_km = row.interval_km
        alert_window_km = row.alert_window_km

        if row.code == "engine_oil":
            interval_km = 5000 if oil_program_km == 5000 else 10000
            alert_window_km = 500 if oil_program_km == 5000 else 900
            interval_days = 183 if oil_program_km == 5000 else 365
            alert_window_days = 30 if oil_program_km == 5000 else 45

        else:
            interval_days = row.interval_days
            alert_window_days = row.alert_window_days
        last_completed_km = int(row.last_completed_km or 0)
        last_completed_at = row.last_completed_at or fallback_completed_at

        due_in_km = None
        due_in_days = None
        progress_candidates = []
        overdue = False
        due_soon = False

        if interval_km is not None:
            used_km = max(0, vehicle_mileage - last_completed_km)
            due_in_km = int(interval_km - used_km)
            progress_candidates.append((used_km / interval_km) * 100 if interval_km > 0 else 100)
            if due_in_km <= 0:
                overdue = True
            elif alert_window_km is not None and due_in_km <= alert_window_km:
                due_soon = True

        if interval_days is not None:
            days_used = max(0, int((now - last_completed_at).total_seconds() // 86400))
            due_in_days = int(interval_days - days_used)
            progress_candidates.append((days_used / interval_days) * 100 if interval_days > 0 else 100)
            if due_in_days <= 0:
                overdue = True
            elif alert_window_days is not None and due_in_days <= alert_window_days:
                due_soon = True

        status = "overdue" if overdue else "due-soon" if due_soon else "healthy"
        progress = int(max(0, min(100, round(max(progress_candidates) if progress_candidates else 0))))

        items.append(
            MaintenanceTaskOut(
                id=row.id,
                code=row.code,
                category=row.category,
                titleEn=row.title_en,
                titleAr=row.title_ar,
                intervalKm=interval_km,
                intervalDays=interval_days,
                dueInKm=due_in_km,
                dueInDays=due_in_days,
                status=status,
                progress=progress,
                lastCompletedKm=last_completed_km,
                lastCompletedAt=last_completed_at,
            )
        )

        alert_candidates.append(
            {
                "task_id": row.id,
                "code": row.code,
                "title_en": row.title_en,
                "title_ar": row.title_ar,
                "status": status,
                "due_in_km": due_in_km,
                "due_in_days": due_in_days,
            }
        )

    vehicle_data = {
        "id": vehicle.id,
        "user_id": vehicle.user_id,
        "vin": vehicle.vin,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
    }
    await notify_maintenance_alerts(db, vehicle_data, alert_candidates, oil_program_km)

    def sort_key(item: MaintenanceTaskOut):
        km_rank = item.dueInKm if item.dueInKm is not None else 10**9
        day_rank = item.dueInDays if item.dueInDays is not None else 10**9
        return min(km_rank, day_rank)

    return sorted(items, key=sort_key)


@router.post("/vehicle/{vehicle_id}/tasks/{task_id}/complete")
async def complete_maintenance_task(
    vehicle_id: UUID,
    task_id: UUID,
    payload: MaintenanceCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    vehicle_query = text("SELECT id, mileage FROM vehicles WHERE id = :vehicle_id AND user_id = :user_id")
    vehicle_result = await db.execute(vehicle_query, {"vehicle_id": vehicle_id, "user_id": current_user.id})
    vehicle = vehicle_result.first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    task_query = text("SELECT id FROM maintenance_tasks WHERE id = :task_id AND is_active = TRUE")
    task_result = await db.execute(task_query, {"task_id": task_id})
    if not task_result.first():
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    upsert_state = text(
        """
        INSERT INTO vehicle_maintenance_state
            (vehicle_id, task_id, last_completed_km, last_completed_at, updated_at)
        VALUES
            (:vehicle_id, :task_id, :completed_km, NOW(), NOW())
        ON CONFLICT (vehicle_id, task_id)
        DO UPDATE SET
            last_completed_km = EXCLUDED.last_completed_km,
            last_completed_at = EXCLUDED.last_completed_at,
            updated_at = NOW()
        """
    )
    await db.execute(
        upsert_state,
        {"vehicle_id": vehicle_id, "task_id": task_id, "completed_km": int(vehicle.mileage or 0)},
    )

    insert_event = text(
        """
        INSERT INTO maintenance_events (vehicle_id, task_id, completed_km, completed_at, notes)
        VALUES (:vehicle_id, :task_id, :completed_km, NOW(), :notes)
        """
    )
    await db.execute(
        insert_event,
        {
            "vehicle_id": vehicle_id,
            "task_id": task_id,
            "completed_km": int(vehicle.mileage or 0),
            "notes": payload.notes,
        },
    )

    await db.commit()
    return {"status": "ok"}
