import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.llm import llm_service
from app.services.notify import notify_owner

logger = logging.getLogger(__name__)


async def _finalize_dtc_report(report_id, dtc_list, vehicle_data, on_report_created=None):
    try:
        logger.warning("[DIAG] Calling Agentic Workflow analyze endpoint")
        llm_result = await llm_service.analyze(
            dtc_codes=dtc_list,
            vehicle={
                "make": vehicle_data.get("make"),
                "model": vehicle_data.get("model"),
                "year": vehicle_data.get("year"),
                "mileage": vehicle_data.get("mileage"),
            },
        )
        logger.warning("[DIAG] Agentic response received with urgency=%s", llm_result.get("urgency"))
    except Exception as exc:
        logger.error("[DIAG] LLM analyze() failed: %s", exc)
        llm_result = {
            "explanation": f"LLM service unavailable. DTC codes: {', '.join(dtc_list)}. Please consult a mechanic.",
            "urgency": "medium",
            "estimated_cost_min": None,
            "estimated_cost_max": None,
        }

    from app.db.session import SessionLocal

    async with SessionLocal() as db:
        update_report = text(
            """
            UPDATE diagnostic_reports
            SET llm_explanation = :expl,
                urgency = :urg,
                estimated_cost_min = :c_min,
                estimated_cost_max = :c_max
            WHERE id = :report_id
            RETURNING *
            """
        )
        result = await db.execute(
            update_report,
            {
                "report_id": report_id,
                "expl": llm_result.get("explanation"),
                "urg": llm_result.get("urgency", "medium"),
                "c_min": llm_result.get("estimated_cost_min"),
                "c_max": llm_result.get("estimated_cost_max"),
            },
        )
        report = result.first()
        await db.commit()

        if report:
            report_data = dict(report._mapping)
            await notify_owner(db, vehicle_data["id"], report_data, vehicle_data)

            if on_report_created:
                await on_report_created(
                    str(vehicle_data["user_id"]),
                    report_data,
                    event_type="diagnostic:analysis_ready",
                )


async def process_dtc_event(db: AsyncSession, payload: dict, on_report_created=None):
    """Process an incoming DTC event from MQTT or the simulation endpoint."""
    logger.warning("[DIAG] Event entered backend diagnostic pipeline")
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
        logger.warning("[DIAG] Processing DTC event for VIN: %s", vin)
        vehicle_query = text("SELECT * FROM vehicles WHERE vin = :vin")
        result = await db.execute(vehicle_query, {"vin": vin})
    elif vehicle_id:
        logger.warning("[DIAG] Processing DTC event for Vehicle ID: %s", vehicle_id)
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
        logger.warning("[DIAG] Duplicate DTC set for vehicle %s — skipping", vin)
        await db.execute(
            text("UPDATE diagnostic_reports SET mileage_at_fault = :mileage WHERE id = :id"),
            {"mileage": mileage, "id": existing.id},
        )
        await db.commit()
        
        # Fetch the full report so we can notify the frontend and stop it from hanging
        full_existing = await db.execute(
            text("SELECT * FROM diagnostic_reports WHERE id = :id"), 
            {"id": existing.id}
        )
        existing_report = full_existing.first()
        if existing_report:
            report_data = dict(existing_report._mapping)
            if on_report_created:
                await on_report_created(str(vehicle_data["user_id"]), report_data)
            return report_data
            
        return None

    # Resolve all previous unresolved reports for this vehicle.
    # A new DTC set represents the current vehicle state, so any codes
    # that are no longer present are considered resolved.
    await db.execute(
        text("""
            UPDATE diagnostic_reports
            SET resolved = TRUE, resolved_at = NOW()
            WHERE vehicle_id = :vehicle_id AND resolved = FALSE
        """),
        {"vehicle_id": vehicle_data["id"]},
    )

    # Store report immediately as pending so the UI can show it right away.
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
            "expl": None,
            "urg": "pending",
            "c_min": None,
            "c_max": None,
        },
    )
    report = result.first()
    report_data = dict(report._mapping)
    await db.commit()

    logger.info("[DIAG] Report %s created for VIN %s", report_data["id"], vin)

    # Broadcast via SSE — cast user_id to str so it matches the SSE dict key
    if on_report_created:
        await on_report_created(str(vehicle_data["user_id"]), report_data)

    # Run AI analysis asynchronously and notify when done.
    asyncio.create_task(
        _finalize_dtc_report(report_data["id"], dtc_list, vehicle_data, on_report_created)
    )

    return report_data
