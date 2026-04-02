from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserOut
from app.services.llm import llm_service

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessageRequest(BaseModel):
    message: str

class ChatSessionResponse(BaseModel):
    sessionId: int
    reply: str

class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None # Or datetime

@router.post("/{report_id}", response_model=ChatSessionResponse)
async def chat_with_mechanic(
    report_id: int,
    chat_req: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    message = chat_req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    # 1. Verify ownership
    report_query = text(
        """
        SELECT dr.*, v.make, v.model, v.year, v.mileage, v.vin
        FROM diagnostic_reports dr
        JOIN vehicles v ON dr.vehicle_id = v.id
        WHERE dr.id = :report_id AND v.user_id = :user_id
        """
    )
    result = await db.execute(report_query, {"report_id": report_id, "user_id": current_user.id})
    report = result.first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # 2. Find or create session
    session_query = text("SELECT id FROM chat_sessions WHERE report_id = :report_id AND user_id = :user_id")
    result = await db.execute(session_query, {"report_id": report_id, "user_id": current_user.id})
    session = result.first()
    
    if session:
        session_id = session.id
    else:
        insert_session = text(
            "INSERT INTO chat_sessions (report_id, user_id) VALUES (:report_id, :user_id) RETURNING id"
        )
        result = await db.execute(insert_session, {"report_id": report_id, "user_id": current_user.id})
        session_id = result.first().id
        await db.commit()

    # 3. Load history
    history_query = text("SELECT role, content FROM chat_messages WHERE session_id = :session_id ORDER BY created_at ASC")
    result = await db.execute(history_query, {"session_id": session_id})
    history = [{"role": row.role, "content": row.content} for row in result.all()]

    # 4. Save user message
    insert_msg = text("INSERT INTO chat_messages (session_id, role, content) VALUES (:session_id, 'user', :content)")
    await db.execute(insert_msg, {"session_id": session_id, "content": message})
    await db.commit()

    # 5. Call LLM
    vehicle = {
        "make": report.make,
        "model": report.model,
        "year": report.year,
        "mileage": report.mileage,
    }
    
    assistant_reply = await llm_service.chat(
        report=dict(report._mapping),
        vehicle=vehicle,
        history=history,
        user_message=message
    )

    # 6. Save assistant reply
    await db.execute(insert_msg, {"session_id": session_id, "content": assistant_reply})
    # Update to 'assistant' role
    update_role = text("UPDATE chat_messages SET role = 'assistant' WHERE session_id = :session_id AND content = :content")
    # Actually I should insert with role correctly the first time
    insert_assistant_msg = text("INSERT INTO chat_messages (session_id, role, content) VALUES (:session_id, 'assistant', :content)")
    await db.execute(insert_assistant_msg, {"session_id": session_id, "content": assistant_reply})
    await db.commit()

    return {"sessionId": session_id, "reply": assistant_reply}

@router.get("/{report_id}/history")
async def get_chat_history(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    session_query = text("SELECT id FROM chat_sessions WHERE report_id = :report_id AND user_id = :user_id")
    result = await db.execute(session_query, {"report_id": report_id, "user_id": current_user.id})
    session = result.first()
    
    if not session:
        return {"sessionId": None, "messages": []}

    history_query = text("SELECT role, content, created_at FROM chat_messages WHERE session_id = :session_id ORDER BY created_at ASC")
    result = await db.execute(history_query, {"session_id": session.id})
    return {"sessionId": session.id, "messages": result.all()}
