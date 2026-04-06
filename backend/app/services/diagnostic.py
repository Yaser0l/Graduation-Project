import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.llm import llm_service
from app.services.notify import notify_owner

logger = logging.getLogger(__name__)


async def process_dtc_event(db: AsyncSession, payload: dict, on_report_created=None):
    """Process an incoming DTC event from MQTT or the simulation endpoint."""
    # Support multiple payload formats (real hardware vs simulation)
    vin = payload.get("vin")
    vehicle_id = payload.get("vehicleId") or payload.get("vehicle_id")

    # Try to extract from nested 'report' if present
    if not vin and not vehicle_id and "report" in payload:
        inner = payload["report"]
        vin = inner.get("vin")
        vehicle_id = inner.get("vehicleId") or inner.get("vehicle_id")

    dtc_list = payload.get("dtc_list") or payload.get("codes")
    if not dtc_list and "report" in payload:
        dtc_list = payload["report"].get("dtc_list") or payload["report"].get("dtc")

    if isinstance(dtc_list, str):
        dtc_list = [dtc_list]
    dtc_list = dtc_list or []

    mileage = payload.get("mileage") or payload.get("odometer") or 0
    if not mileage and "report" in payload:
        mileage = payload["report"].get("mileage") or 0

    # Identify vehicle
    if vin:
        logger.info("[DIAG] Processing DTC event for VIN: %s", vin)
        vehicle_query = text("SELECT * FROM vehicles WHERE vin = :vin")
        result = await db.execute(vehicle_query, {"vin": vin})
    elif vehicle_id:
        logger.info("[DIAG] Processing DTC event for Vehicle ID: %s", vehicle_id)
        vehicle_query = text("SELECT * FROM vehicles WHERE id = :v_id")
        result = await db.execute(vehicle_query, {"v_id": vehicle_id})
    else:
        logger.warning("[DIAG] Rejected — no VIN or Vehicle ID provided.")
        return {"error": "Missing identification"}

    vehicle = result.first()
    if not vehicle:
        logger.warning("[DIAG] Rejected — VIN %s is not registered.", vin)
        return {"error": "Vehicle unregistered"}

    vehicle_data = dict(vehicle._mapping)

    # Update mileage
    await db.execute(
        text("UPDATE vehicles SET mileage = :mileage WHERE id = :id"),
        {"mileage": mileage, "id": vehicle_data["id"]},
    )
    vehicle_data["mileage"] = mileage

    # Deduplication: skip if identical unresolved DTC set already exists
    check_dup = text(
        """
        SELECT id FROM diagnostic_reports
        WHERE vehicle_id = :vehicle_id AND resolved = FALSE AND dtc_codes = :dtc_codes
        """
    )
    result = await db.execute(
        check_dup, {"vehicle_id": vehicle_data["id"], "dtc_codes": dtc_list}
    )
    existing = result.first()

    if existing:
        logger.info("[DIAG] Duplicate DTC set for vehicle %s — skipping", vin)
        await db.execute(
            text("UPDATE diagnostic_reports SET mileage_at_fault = :mileage WHERE id = :id"),
            {"mileage": mileage, "id": existing.id},
        )
        await db.commit()
        return None

    # LLM Analysis — failures are soft: we still save the report
    try:
        llm_result = await llm_service.analyze(
            dtc_codes=dtc_list,
            vehicle={
                "make": vehicle_data.get("make"),
                "model": vehicle_data.get("model"),
                "year": vehicle_data.get("year"),
                "mileage": vehicle_data.get("mileage"),
            },
        )
    except Exception as exc:
        logger.error("[DIAG] LLM analyze() failed: %s", exc)
        llm_result = {
            "explanation": f"LLM service unavailable. DTC codes: {', '.join(dtc_list)}. Please consult a mechanic.",
            "urgency": "medium",
            "estimated_cost_min": None,
            "estimated_cost_max": None,
        }

    # Store report
    insert_report = text(
        """
        INSERT INTO diagnostic_reports
           (vehicle_id, dtc_codes, mileage_at_fault, llm_explanation, urgency, estimated_cost_min, estimated_cost_max)
        VALUES (:v_id, :dtc, :mileage, :expl, :urg, :c_min, :c_max)
        RETURNING *
        """
    )
    result = await db.execute(
        insert_report,
        {
            "v_id": vehicle_data["id"],
            "dtc": dtc_list,
            "mileage": mileage,
            "expl": llm_result["explanation"],
            "urg": llm_result["urgency"],
            "c_min": llm_result["estimated_cost_min"],
            "c_max": llm_result["estimated_cost_max"],
        },
    )
    report = result.first()
    report_data = dict(report._mapping)
    await db.commit()

    logger.info("[DIAG] Report %s created for VIN %s", report_data["id"], vin)

    # Notify vehicle owner via email (non-blocking)
    await notify_owner(db, vehicle_data["id"], report_data, vehicle_data)

    # Broadcast via SSE — cast user_id to str so it matches the SSE dict key
    if on_report_created:
        await on_report_created(str(vehicle_data["user_id"]), report_data)

    return report_data
