import json
from datetime import datetime
from sqlalchemy import text
from app.services.llm import llm_service
from app.services.notify import notify_owner

async def process_dtc_event(db, payload: dict, on_report_created=None):
    # Support multiple formats (real hardware vs simulation)
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
    
    # If it's a single string, convert to list
    if isinstance(dtc_list, str):
        dtc_list = [dtc_list]
    dtc_list = dtc_list or []
    
    mileage = payload.get("mileage") or payload.get("odometer") or 0
    if not mileage and "report" in payload:
        mileage = payload["report"].get("mileage") or 0
    
    # Identify vehicle
    if vin:
        print(f"[DIAG] Processing DTC event for VIN: {vin}")
        vehicle_query = text("SELECT * FROM vehicles WHERE vin = :vin")
        result = await db.execute(vehicle_query, {"vin": vin})
    elif vehicle_id:
        print(f"[DIAG] Processing DTC event for Vehicle ID: {vehicle_id}")
        vehicle_query = text("SELECT * FROM vehicles WHERE id = :v_id")
        result = await db.execute(vehicle_query, {"v_id": vehicle_id})
    else:
        print("[DIAG] Rejected! No VIN or Vehicle ID provided.")
        return {"error": "Missing identification"}

    vehicle = result.first()

    if not vehicle:
        print(f"[DIAG] Rejected! VIN {vin} is not registered.")
        return {"error": "Vehicle unregistered"}

    vehicle_data = dict(vehicle._mapping)
    
    # Update mileage
    update_mileage = text("UPDATE vehicles SET mileage = :mileage WHERE id = :id")
    await db.execute(update_mileage, {"mileage": mileage, "id": vehicle_data["id"]})
    vehicle_data["mileage"] = mileage

    # 2. Deduplication (Postgres handles array comparisons with =)
    check_dup = text(
        """
        SELECT id FROM diagnostic_reports
        WHERE vehicle_id = :vehicle_id AND resolved = FALSE AND dtc_codes = :dtc_codes
        """
    )
    # Note: sqlalchemy can pass list as postgres array if using the right types
    # but since we are using Text queries, we might need a little help.
    # For now, we assume the DB can handle the list.
    result = await db.execute(check_dup, {"vehicle_id": vehicle_data["id"], "dtc_codes": dtc_list})
    existing = result.first()

    if existing:
        print(f"[DIAG] Duplicate DTC set for vehicle {vin} — skipping")
        update_old = text("UPDATE diagnostic_reports SET mileage_at_fault = :mileage WHERE id = :id")
        await db.execute(update_old, {"mileage": mileage, "id": existing.id})
        await db.commit()
        return None

    # 3. LLM Analysis
    llm_result = await llm_service.analyze(
        dtc_codes=dtc_list,
        vehicle={
            "make": vehicle_data.get("make"),
            "model": vehicle_data.get("model"),
            "year": vehicle_data.get("year"),
            "mileage": vehicle_data.get("mileage")
            }
    )

    # 4. Store Report
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
            "c_max": llm_result["estimated_cost_max"]
        }
    )
    report = result.first()
    report_data = dict(report._mapping)
    await db.commit()

    print(f"[DIAG] Report {report_data['id']} created for VIN {vin}")

    # 5. Notify
    await notify_owner(db, vehicle_data["id"], report_data, vehicle_data)

    # 6. Callback for SSE
    if on_report_created:
        await on_report_created(vehicle_data["user_id"], report_data)

    return report_data
