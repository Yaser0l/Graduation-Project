from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
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


class PublishDtcMqttRequest(BaseModel):
    vin: Optional[str] = None
    vehicle_id: Optional[str] = None
    dtc_list: List[str]
    mileage: Optional[int] = 0
    timestamp: Optional[str] = None
    topic: Optional[str] = None


@router.post("/simulate-dtc")
async def simulate_dtc(
    req: SimulateDtcRequest,
    db: AsyncSession = Depends(get_db),
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
            "year": req.year,
        },
        on_report_created=on_report_created,
    )

    if report and "error" in report:
        if report["error"] == "Vehicle unregistered":
            raise HTTPException(status_code=401, detail="VIN not registered.")
        return report

    if report:
        return {"message": "Simulated DTC processed — new report created", "report": report}
    return {"message": "DTC already known (deduplicated) — no new report"}


@router.post("/publish-dtc-mqtt")
async def publish_dtc_mqtt(
    req: PublishDtcMqttRequest,
    request: Request,
):
    if settings.ENV != "development":
        raise HTTPException(status_code=403, detail="MQTT publishing only available in development")

    if not req.dtc_list:
        raise HTTPException(status_code=400, detail="dtc_list is required")
    if not req.vin and not req.vehicle_id:
        raise HTTPException(status_code=400, detail="vin or vehicle_id is required")

    mqtt_svc = getattr(request.app.state, "mqtt_svc", None)
    if not mqtt_svc:
        raise HTTPException(status_code=503, detail="MQTT service is not initialized")

    event_timestamp = req.timestamp or datetime.now(timezone.utc).isoformat()
    topic = req.topic or f"vehicle/{(req.vin or req.vehicle_id)}/dtc"
    payload = {
        "vin": req.vin,
        "vehicle_id": req.vehicle_id,
        "dtc_list": req.dtc_list,
        "mileage": req.mileage or 0,
        "timestamp": event_timestamp,
    }

    await mqtt_svc.publish(topic, payload, qos=1, retain=False)

    return {
        "message": "DTC event published to MQTT",
        "topic": topic,
        "payload": payload,
    }


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database disconnected: {e}")
