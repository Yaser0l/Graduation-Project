from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.config import settings
from app.services.diagnostic import process_dtc_event
from app.core.sse import on_report_created

router = APIRouter(prefix="/api/internal", tags=["internal"])

class SimulateDtcRequest(BaseModel):
    vin: str
    dtc_list: List[str]
    mileage: Optional[int] = 0
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None

@router.post("/simulate-dtc")
async def simulate_dtc(
    req: SimulateDtcRequest,
    db: AsyncSession = Depends(get_db)
):
    if settings.ENV != "development":
        raise HTTPException(status_code=403, detail="Simulation only available in development")

    if not req.vin or not req.dtc_list:
        raise HTTPException(status_code=400, detail="vin and dtc_list are required")

    report = await process_dtc_event(
        db,
        {
            "vin": req.vin,
            "dtc_list": req.dtc_list,
            "mileage": req.mileage,
            "make": req.make,
            "model": req.model,
            "year": req.year
        },
        on_report_created=on_report_created
    )

    if report and "error" in report:
        if report["error"] == "Vehicle unregistered":
            raise HTTPException(status_code=401, detail="VIN not registered.")
        return report
    
    if report:
        return {"message": "Simulated DTC processed — new report created", "report": report}
    else:
        return {"message": "DTC already known (deduplicated) — no new report"}

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database disconnected: {e}")
            
