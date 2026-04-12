from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from uuid import UUID
import json
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserOut
from app.services.llm import llm_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    message: str
    stream_mode: str = "word"
    stream_chunk_size: int = 2


@router.post("/{report_id}")
async def chat_with_mechanic(
    report_id: UUID,
    chat_req: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    message = chat_req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Verify ownership
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

    # Find or create session
    session_query = text(
        "SELECT id FROM chat_sessions WHERE report_id = :report_id AND user_id = :user_id"
    )
    result = await db.execute(session_query, {"report_id": report_id, "user_id": current_user.id})
    session = result.first()

    if session:
        session_id = session.id
    else:
        insert_session = text(
            "INSERT INTO chat_sessions (report_id, user_id) VALUES (:report_id, :user_id) RETURNING id"
        )
        result = await db.execute(
            insert_session, {"report_id": report_id, "user_id": current_user.id}
        )
        session_id = result.first().id
        await db.commit()

    # Load history
    history_query = text(
        "SELECT role, content FROM chat_messages WHERE session_id = :session_id ORDER BY created_at ASC"
    )
    result = await db.execute(history_query, {"session_id": session_id})
    history = [{"role": row.role, "content": row.content} for row in result.all()]

    # Save user message
    await db.execute(
        text("INSERT INTO chat_messages (session_id, role, content) VALUES (:session_id, 'user', :content)"),
        {"session_id": session_id, "content": message},
    )
    await db.commit()

    # Call LLM service
    vehicle = {
        "make": report.make,
        "model": report.model,
        "year": report.year,
        "mileage": report.mileage,
    }

    stream_mode = (chat_req.stream_mode or "word").lower()
    if stream_mode not in {"word", "char"}:
        stream_mode = "word"
    stream_chunk_size = max(1, min(int(chat_req.stream_chunk_size or 2), 12))

    async def event_stream():
        assistant_reply_parts = []
        done_reply = None
        has_error = False
        try:
            async for upstream_event in llm_service.chat_stream(
                report=dict(report._mapping),
                vehicle=vehicle,
                history=history,
                user_message=message,
                stream_mode=stream_mode,
                stream_chunk_size=stream_chunk_size,
            ):
                event_type = upstream_event.get("event")
                if event_type == "token":
                    assistant_reply_parts.append(upstream_event.get("chunk") or "")
                elif event_type == "done":
                    done_reply = upstream_event.get("reply")
                elif event_type == "error":
                    has_error = True
                yield json.dumps(upstream_event, ensure_ascii=False) + "\n"

            assistant_reply = (done_reply or "".join(assistant_reply_parts)).strip()
            if assistant_reply and not has_error:
                await db.execute(
                    text("INSERT INTO chat_messages (session_id, role, content) VALUES (:session_id, 'assistant', :content)"),
                    {"session_id": session_id, "content": assistant_reply},
                )
                await db.commit()
            elif not has_error:
                fallback = "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment."
                await db.execute(
                    text("INSERT INTO chat_messages (session_id, role, content) VALUES (:session_id, 'assistant', :content)"),
                    {"session_id": session_id, "content": fallback},
                )
                await db.commit()
                yield json.dumps({"event": "done", "sessionId": str(session_id), "reply": fallback}, ensure_ascii=False) + "\n"
        except Exception:
            await db.rollback()
            yield json.dumps(
                {
                    "event": "error",
                    "message": "Sorry, an error occurred while generating the AI reply.",
                    "sessionId": str(session_id),
                }
            , ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/{report_id}/history")
async def get_chat_history(
    report_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    session_query = text(
        "SELECT id FROM chat_sessions WHERE report_id = :report_id AND user_id = :user_id"
    )
    result = await db.execute(
        session_query, {"report_id": report_id, "user_id": current_user.id}
    )
    session = result.first()

    if not session:
        return {"sessionId": None, "messages": []}

    history_query = text(
        """
        SELECT role, content, created_at FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        LIMIT :limit OFFSET :offset
        """
    )
    result = await db.execute(
        history_query, {"session_id": session.id, "limit": limit, "offset": offset}
    )
    messages = [
        {
            "role": row.role,
            "content": row.content,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.all()
    ]
    return {"sessionId": session.id, "messages": messages}
