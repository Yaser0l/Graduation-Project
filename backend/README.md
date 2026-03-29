# CarBrain Backend

> **Developer 2** — Backend, Database & APIs for the OBD-2 Car Diagnostics platform.

## Quick Start

### 1. Prerequisites

- **Node.js 18+**
- **PostgreSQL 14+**
- (Optional) MQTT broker like [Mosquitto](https://mosquitto.org/)

### 2. Install

```bash
cd backend
npm install
```

### 3. Environment

```bash
cp .env.example .env
# Edit .env with your database credentials, JWT secret, etc.
```

**Minimum required** for local dev:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=carbrain
DB_USER=postgres
DB_PASSWORD=your_password
JWT_SECRET=any_random_string_here
```

### 4. Create Database

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE carbrain;"

# Run the schema
psql -U postgres -d carbrain -f src/db/schema.sql
```

### 5. Run

```bash
npm run dev
```

The server starts at `http://localhost:4000`.

---

## API Reference

### Auth

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | `{ name, email, password }` | Create account → returns JWT |
| POST | `/api/auth/login` | `{ email, password }` | Login → returns JWT |
| POST | `/api/auth/push-subscribe` | `{ subscription }` | Save WebPush subscription (auth required) |

### Vehicles (Auth Required)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/api/vehicles` | — | List user's vehicles |
| GET | `/api/vehicles/:id` | — | Get vehicle detail |
| POST | `/api/vehicles` | `{ vin, make, model, year, mileage }` | Register vehicle |
| PATCH | `/api/vehicles/:id` | `{ make?, model?, year?, mileage? }` | Update vehicle |
| DELETE | `/api/vehicles/:id` | — | Delete vehicle |

### Diagnostics (Auth Required)

| Method | Endpoint | Query | Description |
|--------|----------|-------|-------------|
| GET | `/api/diagnostics` | `?resolved=true\|false` | All user's reports |
| GET | `/api/diagnostics/:id` | — | Single report detail |
| PATCH | `/api/diagnostics/:id/resolve` | — | Mark resolved |
| GET | `/api/diagnostics/vehicle/:vehicleId` | — | Reports per vehicle |

### Chat (Auth Required)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/chat/:reportId` | `{ message }` | Chat with AI about a report |
| GET | `/api/chat/:reportId/history` | — | Get full conversation |

### Internal / Dev

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/internal/simulate-dtc` | `{ vin, dtc_list, mileage }` | Simulate OBD-II event |
| GET | `/api/internal/health` | — | Health check |

### Real-Time Events (SSE)

```
GET /api/events?token=<JWT>
```

Server-Sent Events stream. Emits `diagnostic:new` when a new report is created.

---

## MQTT Protocol

The backend subscribes to: `obd2/dtc/#`

**Expected message format (JSON):**

```json
{
  "vin": "1HGBH41JXMN109186",
  "dtc_list": ["P0420", "P0171"],
  "mileage": 87432,
  "timestamp": "2026-03-29T08:30:00Z"
}
```

---

## Database Schema

5 tables: `users`, `vehicles`, `diagnostic_reports`, `chat_sessions`, `chat_messages`.

Full DDL: [`src/db/schema.sql`](src/db/schema.sql)

---

## Project Structure

```
backend/
├── src/
│   ├── config/           # env, db pool, mqtt, mailer, webpush
│   ├── db/               # schema.sql + query helpers
│   ├── mqtt/             # MQTT subscriber
│   ├── services/         # LLM, notification, diagnostic orchestration
│   ├── routes/           # Express route handlers
│   ├── middleware/        # JWT auth, error handler
│   └── app.js            # Entry point
├── .env.example
├── package.json
└── README.md
```
