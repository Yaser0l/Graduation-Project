from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserOut
from app.schemas.diagnostic import DiagnosticReportOut

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

@router.get("/", response_model=List[DiagnosticReportOut])
async def get_diagnostics(
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    sql = """
        SELECT dr.*, v.vin, v.make, v.model, v.year
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE v.user_id = :user_id
    """
    params = {"user_id": current_user.id}

    if resolved is True:
        sql += " AND dr.resolved = TRUE"
    elif resolved is False:
        sql += " AND dr.resolved = FALSE"

    sql += " ORDER BY dr.created_at DESC"
    
    result = await db.execute(text(sql), params)
    return result.all()

@router.get("/{report_id}", response_model=DiagnosticReportOut)
async def get_diagnostic(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    sql = """
        SELECT dr.*, v.vin, v.make, v.model, v.year, v.mileage AS current_mileage
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE dr.id = :report_id AND v.user_id = :user_id
    """
    result = await db.execute(text(sql), {"report_id": report_id, "user_id": current_user.id})
    report = result.first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.patch("/{report_id}/resolve", response_model=DiagnosticReportOut)
async def resolve_diagnostic(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    sql = """
        UPDATE diagnostic_reports dr
        SET resolved = TRUE, resolved_at = NOW()
        FROM vehicles v
        WHERE dr.id = :report_id AND dr.vehicle_id = v.id AND v.user_id = :user_id
        RETURNING dr.*, v.vin, v.make, v.model, v.year
    """
    result = await db.execute(text(sql), {"report_id": report_id, "user_id": current_user.id})
    report = result.first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.commit()
    return report

@router.get("/vehicle/{vehicle_id}", response_model=List[DiagnosticReportOut])
async def get_vehicle_diagnostics(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    sql = """
        SELECT dr.*
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE v.id = :vehicle_id AND v.user_id = :user_id
        ORDER BY dr.created_at DESC
    """
    result = await db.execute(text(sql), {"vehicle_id": vehicle_id, "user_id": current_user.id})
    return result.all()
