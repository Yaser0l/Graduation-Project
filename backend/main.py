import uvicorn
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, status, Request
from fastapi.responses import JSONResponse

from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from jose import jwt, JWTError

from app.core.config import settings
from app.routers import auth, vehicle, diagnostic, chat, internal, maintenance
from app.core.mqtt import MqttService
from app.core.sse import on_report_created, sse_service
from app.db.session import init_db

# For rate limiting
RATE_LIMIT = 60
RATE_WINDOW = 60
request_counts = defaultdict(list)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create DB tables if they don't exist
    await init_db()

    # Startup: Initialize MQTT
    mqtt_svc = MqttService(on_report_created_cb=on_report_created)
    app.state.mqtt_svc = mqtt_svc
    try:
        await mqtt_svc.connect()
        print("[LIFESPAN] MQTT Connected")
    except Exception as e:
        print(f"[LIFESPAN] MQTT connection failed: {e}")
    
    yield
    
    # Shutdown: Disconnect MQTT
    try:
        await mqtt_svc.disconnect()
        print("[LIFESPAN] MQTT Disconnected")
    except Exception as e:
        print(f"[LIFESPAN] MQTT disconnect failed: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Rate Limiting Middleware
MAX_TRACKED_IPS = 1000

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    if len(request_counts) > MAX_TRACKED_IPS:
        request_counts.clear()
    
    # clean up old reqs
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_WINDOW]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
    
    request_counts[client_ip].append(now)
    response = await call_next(request)
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE events endpoint (mirrors app.js GET /api/events)
@app.get(f"{settings.API_V1_STR}/events")
async def events_handler(token: str = Query(...)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
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
app.include_router(maintenance.router)

@app.get("/")
async def root():
    return {"message": "CarBrain Backend is running (FastAPI)"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
