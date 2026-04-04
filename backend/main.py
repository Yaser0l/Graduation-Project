import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Query, HTTPException, status

# Silence the (trapped) bcrypt error from passlib
logging.getLogger("passlib").setLevel(logging.ERROR)
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from jose import jwt, JWTError

from app.core.config import settings
from app.routers import auth, vehicle, diagnostic, chat, internal
from app.core.mqtt import MqttService
from app.core.sse import on_report_created, sse_service
from app.db.init_db import init_db_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema exists
    await init_db_schema()

    # Startup: Initialize MQTT
    mqtt_svc = MqttService(on_report_created_cb=on_report_created)
    try:
        await mqtt_svc.connect()
        print("[LIFESPAN] MQTT Connected")
    except Exception as e:
        print(f"[LIFESPAN] MQTT connection failed: {e}")

    yield

    # Shutdown: Disconnect MQTT
    await mqtt_svc.disconnect()
    print("[LIFESPAN] MQTT Disconnected")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SSE events endpoint (mirrors app.js GET /api/events)
@app.get(f"{settings.API_V1_STR}/events")
async def events_handler(token: str = Query(...)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required"
        )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = user_id_str
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    return EventSourceResponse(sse_service.subscribe(user_id))


# Mount Routers
app.include_router(auth.router)
app.include_router(vehicle.router)
app.include_router(diagnostic.router)
app.include_router(chat.router)
app.include_router(internal.router)


@app.get("/")
async def root():
    return {"message": "CarBrain Backend is running (FastAPI)"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
