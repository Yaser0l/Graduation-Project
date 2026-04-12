from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserOut
from app.schemas.diagnostic import DiagnosticReportOut, FullReportRequest
from app.services.llm import llm_service

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("/", response_model=List[DiagnosticReportOut])
async def get_diagnostics(
    resolved: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    sql = """
        SELECT dr.*, v.vin, v.make, v.model, v.year
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE v.user_id = :user_id
    """
    params = {"user_id": current_user.id, "limit": limit, "offset": offset}

    if resolved is True:
        sql += " AND dr.resolved = TRUE"
    elif resolved is False:
        sql += " AND dr.resolved = FALSE"

    sql += " ORDER BY dr.created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(sql), params)
    return result.all()


@router.get("/vehicle/{vehicle_id}", response_model=List[DiagnosticReportOut])
async def get_vehicle_diagnostics(
    vehicle_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    sql = """
        SELECT dr.*
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE v.id = :vehicle_id AND v.user_id = :user_id
        ORDER BY dr.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    result = await db.execute(
        text(sql),
        {"vehicle_id": vehicle_id, "user_id": current_user.id, "limit": limit, "offset": offset},
    )
    return result.all()


@router.get("/{report_id}", response_model=DiagnosticReportOut)
async def get_diagnostic(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
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
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
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


@router.post("/{report_id}/full-report")
async def generate_full_report(
    report_id: UUID,
    payload: FullReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """Triggers the full multi-agent diagnostic analysis for a report."""
    sql = """
        SELECT dr.*, v.make, v.model, v.year, v.mileage, v.vin
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE dr.id = :report_id AND v.user_id = :user_id
    """
    result = await db.execute(text(sql), {"report_id": report_id, "user_id": current_user.id})
    report = result.first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    dtc_codes = report.dtc_codes if report.dtc_codes else []
    vehicle = {
        "make": report.make,
        "model": report.model,
        "year": report.year,
        "mileage": report.mileage,
    }

    full_result = await llm_service.full_report(
        dtc_codes=dtc_codes,
        vehicle=vehicle,
        language=(payload.language or "en"),
    )
    return full_result
