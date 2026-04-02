import aiosmtplib
from uuid import UUID
from email.message import EmailMessage
from app.core.config import settings

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
        await aiosmtplib.send(
            message,
            hostname=settings.MAIL_HOST,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USER,
            password=settings.MAIL_PASSWORD,
            use_tls=(settings.MAIL_PORT == 465),
            start_tls=(settings.MAIL_PORT == 587),
        )
        print(f"[NOTIFY] Email sent to {to_email}")
    except Exception as e:
        print(f"[NOTIFY] Failed to send email: {e}")

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
