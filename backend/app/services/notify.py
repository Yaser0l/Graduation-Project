import aiosmtplib
from uuid import UUID
from email.message import EmailMessage
from app.core.config import settings


async def _send_email_message(message: EmailMessage):
    await aiosmtplib.send(
        message,
        hostname=settings.MAIL_HOST,
        port=settings.MAIL_PORT,
        username=settings.MAIL_USER,
        password=settings.MAIL_PASSWORD,
        use_tls=(settings.MAIL_PORT == 465),
        start_tls=(settings.MAIL_PORT == 587),
    )

async def send_email_alert(to_email: str, report: dict, vehicle: dict):
    urgency_colors = {
        "low": "#22c55e",
        "medium": "#eab308",
        "high": "#f97316",
        "critical": "#ef4444",
    }
    color = urgency_colors.get(report.get("urgency"), "#6b7280")

    dtc_codes = ", ".join(report.get("dtc_codes", []))
    urgency_upper = report.get("urgency", "unknown").upper()
    
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:{color}">⚠️ Diagnostic Alert — {urgency_upper}</h2>
      <p><strong>Vehicle:</strong> {vehicle.get('year') or ''} {vehicle.get('make') or ''} {vehicle.get('model') or ''} ({vehicle.get('vin')})</p>
      <p><strong>Trouble Codes:</strong> {dtc_codes}</p>
      <hr/>
      <div style="background:#f9fafb;padding:16px;border-radius:8px">
        {report.get('llm_explanation')}
      </div>
      <br/>
      <p>Log in to <strong>CarBrain</strong> to chat with the AI Mechanic for more details.</p>
    </div>
    """

    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to_email
    message["Subject"] = f"🚗 CarBrain Alert: {dtc_codes} — {urgency_upper}"
    message.set_content(html, subtype="html")

    try:
        if not settings.MAIL_USER or not settings.MAIL_PASSWORD:
            print(f"[NOTIFY] no sender email")
            return
            
        await _send_email_message(message)
        print(f"[NOTIFY] Email sent to {to_email}")
    except Exception as e:
        print(f"[NOTIFY] Failed to send email: {e}")


async def send_maintenance_alert(to_email: str, vehicle: dict, task: dict):
    status = (task.get("status") or "due-soon").lower()
    status_label = "OVERDUE" if status == "overdue" else "DUE SOON"
    status_color = "#ef4444" if status == "overdue" else "#f59e0b"

    due_parts = []
    if task.get("due_in_km") is not None:
        due_parts.append(f"{task['due_in_km']} km")
    if task.get("due_in_days") is not None:
        due_parts.append(f"{task['due_in_days']} day(s)")
    due_text = " / ".join(due_parts) if due_parts else "N/A"

    task_title = task.get("title_en") or task.get("code") or "Maintenance Task"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:{status_color}">🛠️ Maintenance Alert — {status_label}</h2>
      <p><strong>Vehicle:</strong> {vehicle.get('year') or ''} {vehicle.get('make') or ''} {vehicle.get('model') or ''} ({vehicle.get('vin')})</p>
      <p><strong>Task:</strong> {task_title}</p>
      <p><strong>Due In:</strong> {due_text}</p>
      <hr/>
      <p>Please schedule this maintenance in CarBrain.</p>
    </div>
    """

    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to_email
    message["Subject"] = f"🛠️ CarBrain Maintenance Alert: {task_title} ({status_label})"
    message.set_content(html, subtype="html")

    try:
        if not settings.MAIL_USER or not settings.MAIL_PASSWORD:
            print(f"[NOTIFY] no sender email")
            return True

        await _send_email_message(message)
        print(f"[NOTIFY] email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[NOTIFY] Failed to send maintenance email: {e}")
        return False

async def notify_owner(db, vehicle_id: UUID, report: dict, vehicle: dict):
    from sqlalchemy import text
    try:
        query = text("SELECT email FROM users WHERE id = :id")
        result = await db.execute(query, {"id": vehicle.get("user_id")})
        user = result.first()
        
        if not user:
            print(f"[NOTIFY] No user found for vehicle {vehicle_id}")
            return
            
        await send_email_alert(user.email, report, vehicle)
    except Exception as e:
        print(f"[NOTIFY] notify_owner error: {e}")


async def notify_maintenance_alerts(db, vehicle: dict, tasks: list[dict], oil_program_km: int = 10000):
    from sqlalchemy import text

    try:
        query = text("SELECT email FROM users WHERE id = :id")
        result = await db.execute(query, {"id": vehicle.get("user_id")})
        user = result.first()
        if not user:
            print(f"[NOTIFY] No user found for vehicle {vehicle.get('id')}")
            return

        insert_notification = text(
            """
            INSERT INTO maintenance_alert_notifications (vehicle_id, task_id, alert_type)
            VALUES (:vehicle_id, :task_id, :alert_type)
            ON CONFLICT (vehicle_id, task_id, alert_type) DO NOTHING
            RETURNING id
            """
        )

        for task in tasks:
            status = (task.get("status") or "").lower()
            if status not in ("due-soon", "overdue"):
                continue

            # Engine oil alerts depend on selected program (5000 vs 10000),
            # so include it in dedup key to avoid cross-plan suppression.
            alert_type_key = status
            if task.get("code") == "engine_oil":
                plan_km = 5000 if int(oil_program_km or 10000) == 5000 else 10000
                alert_type_key = f"{status}-{plan_km}"

            inserted = await db.execute(
                insert_notification,
                {
                    "vehicle_id": vehicle.get("id"),
                    "task_id": task.get("task_id"),
                    "alert_type": alert_type_key,
                },
            )
            if inserted.first():
                import asyncio
                asyncio.create_task(send_maintenance_alert(user.email, vehicle, task))

        await db.commit()
    except Exception as e:
        print(f"[NOTIFY] notify_maintenance_alerts error: {e}")
