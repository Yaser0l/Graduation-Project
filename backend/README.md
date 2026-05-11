# CarBrain Backend

FastAPI backend for the CarBrain OBD-2 diagnostics platform. It exposes REST APIs, streams SSE events, consumes MQTT DTC events, and integrates with the Agentic Workflow LLM service.

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 14+
- MQTT broker (Mosquitto or similar)
- Optional: Agentic Workflow LLM service

### 2. Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment

```bash
cp .env.example .env
# Edit .env with your database credentials, JWT secret, etc.
```

Minimum required for local dev:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password_here@localhost:5432/carbrain
JWT_SECRET=change_me_to_a_random_64_char_string
```

### 4. Create Database

```bash
psql -U postgres -c "CREATE DATABASE carbrain;"
```

Tables are created automatically on startup using [app/db/schema.sql](app/db/schema.sql).

### 5. Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

The server starts at http://localhost:5000. API docs are at http://localhost:5000/docs.

## Docker Compose

The compose file starts Postgres, Mosquitto, and the FastAPI service.

```bash
cd backend
docker compose up --build
```

## Environment Variables

These are loaded from .env (see [.env.example](.env.example)).

- Server: `PROJECT_NAME`, `API_V1_STR`, `ENV`, `PORT`
- Database: `DATABASE_URL`
- Auth: `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- MQTT: `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`, `MQTT_TOPIC_DTC`
- LLM: `LLM_BASE_URL`, `LLM_ANALYZE_PATH`, `LLM_CHAT_PATH`, `LLM_FULL_REPORT_PATH`, `LLM_API_KEY`, `INTERNAL_API_SECRET`
- Mailer: `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_FROM`

## API Reference

All protected routes expect `Authorization: Bearer <JWT>`.

### Auth

| Method | Endpoint             | Body                               | Description                 |
| ------ | -------------------- | ---------------------------------- | --------------------------- |
| POST   | `/api/auth/register` | `{ name, email, password }`        | Create account, returns JWT |
| POST   | `/api/auth/login`    | form data (`username`, `password`) | Login, returns JWT          |

### Vehicles (Auth Required)

| Method | Endpoint                     | Body                                                                                                                          | Description          |
| ------ | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| GET    | `/api/vehicles`              | —                                                                                                                             | List user's vehicles |
| POST   | `/api/vehicles`              | `{ vin, make, model, year, mileage, oil_program_km, initialize_maintenance_baseline?, last_service_km?, last_service_date? }` | Register vehicle     |
| GET    | `/api/vehicles/{vehicle_id}` | —                                                                                                                             | Get vehicle detail   |
| PATCH  | `/api/vehicles/{vehicle_id}` | `{ mileage }`                                                                                                                 | Update mileage       |
| DELETE | `/api/vehicles/{vehicle_id}` | —                                                                                                                             | Delete vehicle       |

### Diagnostics (Auth Required)

| Method | Endpoint                                   | Query                         | Description                 |
| ------ | ------------------------------------------ | ----------------------------- | --------------------------- |
| GET    | `/api/diagnostics`                         | `resolved`, `limit`, `offset` | All user's reports          |
| GET    | `/api/diagnostics/vehicle/{vehicle_id}`    | `limit`, `offset`             | Reports for a vehicle       |
| GET    | `/api/diagnostics/{report_id}`             | —                             | Report detail               |
| PATCH  | `/api/diagnostics/{report_id}/resolve`     | —                             | Mark resolved               |
| POST   | `/api/diagnostics/{report_id}/full-report` | `{ language? }`               | Stream full report (NDJSON) |

### Chat (Auth Required)

| Method | Endpoint                        | Body                                            | Description             |
| ------ | ------------------------------- | ----------------------------------------------- | ----------------------- |
| POST   | `/api/chat/{report_id}`         | `{ message, stream_mode?, stream_chunk_size? }` | Stream AI chat (NDJSON) |
| GET    | `/api/chat/{report_id}/history` | `limit`, `offset`                               | Get full conversation   |

### Maintenance (Auth Required)

| Method | Endpoint                                                         | Body         | Description                   |
| ------ | ---------------------------------------------------------------- | ------------ | ----------------------------- |
| GET    | `/api/maintenance/vehicle/{vehicle_id}`                          | —            | Maintenance status and alerts |
| POST   | `/api/maintenance/vehicle/{vehicle_id}/tasks/{task_id}/complete` | `{ notes? }` | Mark task complete            |

### Internal / Dev

| Method | Endpoint                         | Body                                                            | Description                            |
| ------ | -------------------------------- | --------------------------------------------------------------- | -------------------------------------- |
| POST   | `/api/internal/simulate-dtc`     | `{ vin, dtc_list, mileage?, make?, model?, year? }`             | Simulate DTC event (development only)  |
| POST   | `/api/internal/publish-dtc-mqtt` | `{ vin?, vehicle_id?, dtc_list, mileage?, timestamp?, topic? }` | Publish DTC to MQTT (development only) |
| GET    | `/api/internal/health`           | —                                                               | Health check                           |

### Real-Time Events (SSE)

```
GET /api/events?token=<JWT>
```

Server-Sent Events stream. Emits `diagnostic:new` for new reports.

## MQTT Protocol

The backend subscribes to `MQTT_TOPIC_DTC` (default: `vehicle/+/dtc`).

Expected message format (JSON):

```json
{
  "vin": "1HGBH41JXMN109186",
  "dtc_list": ["P0420", "P0171"],
  "mileage": 87432,
  "timestamp": "2026-03-29T08:30:00Z"
}
```

## Database Schema

The schema is defined in [app/db/schema.sql](app/db/schema.sql). It includes users, vehicles, diagnostic reports, chat sessions/messages, and maintenance tracking tables.

## Project Structure

```
backend/
├── app/
│   ├── core/        # config, deps, mqtt, sse, security
│   ├── db/          # schema.sql + session
│   ├── routers/     # FastAPI routers
│   ├── schemas/     # Pydantic models
│   └── services/    # LLM, diagnostic, notifications
├── main.py          # FastAPI entry point
├── .env.example
├── requirements.txt
└── README.md
```
