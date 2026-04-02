import json
from datetime import datetime
from sqlalchemy import text
from app.services.llm import llm_service
from app.services.notify import notify_owner

async def process_dtc_event(db, payload: dict, on_report_created=None):
    vin = payload.get("vin")
    dtc_list = payload.get("dtc_list", [])
    mileage = payload.get("mileage", 0)
    
    print(f"[DIAG] Processing DTC event: VIN={vin}, codes={','.join(dtc_list)}, mileage={mileage}")

    # 1. Find vehicle
    vehicle_query = text("SELECT * FROM vehicles WHERE vin = :vin")
    result = await db.execute(vehicle_query, {"vin": vin})
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
            "mileage": vehicle_data.get("mileage"),
            "last_oil_change_km": vehicle_data.get("last_oil_change_km"),
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
