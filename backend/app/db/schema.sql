-- ============================================================
-- CarBrain — Database Schema
-- Run:  psql -U postgres -f schema.sql
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ──────────────────────────────────────────────────────────────
-- 1. USERS
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(120)  NOT NULL,
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ──────────────────────────────────────────────────────────────
-- 2. VEHICLES
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicles (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vin               VARCHAR(17)   NOT NULL UNIQUE,
    make              VARCHAR(60),
    model             VARCHAR(60),
    year              INTEGER,
    mileage           INTEGER       DEFAULT 0,
    oil_program_km    INTEGER       NOT NULL DEFAULT 10000,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicles_user  ON vehicles (user_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_vin   ON vehicles (vin);

-- ──────────────────────────────────────────────────────────────
-- 3. DIAGNOSTIC REPORTS
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id        UUID          NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    dtc_codes         TEXT[]        NOT NULL,          -- e.g. {P0420, P0171}
    mileage_at_fault  INTEGER,
    llm_explanation   TEXT,                            -- Raw LLM markdown / text
    urgency           VARCHAR(20)   DEFAULT 'medium',  -- low | medium | high | critical
    estimated_cost_min INTEGER      DEFAULT NULL,
    estimated_cost_max INTEGER      DEFAULT NULL,
    resolved          BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    resolved_at       TIMESTAMPTZ   DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_diag_vehicle   ON diagnostic_reports (vehicle_id);
CREATE INDEX IF NOT EXISTS idx_diag_resolved  ON diagnostic_reports (resolved);

-- ──────────────────────────────────────────────────────────────
-- 4. CHAT SESSIONS (linked to a specific report)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id    UUID          NOT NULL REFERENCES diagnostic_reports(id) ON DELETE CASCADE,
    user_id      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_report ON chat_sessions (report_id);

-- ──────────────────────────────────────────────────────────────
-- 5. CHAT MESSAGES (individual messages within a session)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID          NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role         VARCHAR(20)   NOT NULL,   -- 'user' | 'assistant'
    content      TEXT          NOT NULL,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 6. MAINTENANCE TASK DEFINITIONS (global catalog)
CREATE TABLE IF NOT EXISTS maintenance_tasks (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code               VARCHAR(60) NOT NULL UNIQUE,   -- e.g. engine_oil, gear_oil, air_filter
    title_en           VARCHAR(120) NOT NULL,
    title_ar           VARCHAR(120) NOT NULL,
    category           VARCHAR(60)  NOT NULL,         -- Engine, Transmission, Cooling...
    interval_km        INTEGER      DEFAULT NULL,     -- nullable: time-only tasks allowed
    interval_days      INTEGER      DEFAULT NULL,     -- nullable: mileage-only tasks allowed
    alert_window_km    INTEGER      DEFAULT NULL,
    alert_window_days  INTEGER      DEFAULT NULL,
    is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maint_tasks_active ON maintenance_tasks (is_active);

-- 7. PER-VEHICLE MAINTENANCE BASELINE (current state by vehicle/task)
CREATE TABLE IF NOT EXISTS vehicle_maintenance_state (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id           UUID         NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    task_id              UUID         NOT NULL REFERENCES maintenance_tasks(id) ON DELETE CASCADE,
    last_completed_km    INTEGER      DEFAULT 0,
    last_completed_at    TIMESTAMPTZ  DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (vehicle_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_vehicle_maint_state_vehicle ON vehicle_maintenance_state (vehicle_id);

-- 8. MAINTENANCE EVENTS (history / audit)
CREATE TABLE IF NOT EXISTS maintenance_events (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id           UUID         NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    task_id              UUID         NOT NULL REFERENCES maintenance_tasks(id) ON DELETE CASCADE,
    completed_km         INTEGER      NOT NULL,
    completed_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    notes                TEXT         DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_maint_events_vehicle ON maintenance_events (vehicle_id);
CREATE INDEX IF NOT EXISTS idx_maint_events_task    ON maintenance_events (task_id);

-- 9. MAINTENANCE ALERT NOTIFICATION LOG (email dedupe)
CREATE TABLE IF NOT EXISTS maintenance_alert_notifications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id    UUID         NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    task_id       UUID         NOT NULL REFERENCES maintenance_tasks(id) ON DELETE CASCADE,
    alert_type    VARCHAR(20)  NOT NULL,  -- due-soon | overdue
    notified_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (vehicle_id, task_id, alert_type)
);

CREATE INDEX IF NOT EXISTS idx_maint_alert_notif_vehicle ON maintenance_alert_notifications (vehicle_id);


CREATE INDEX IF NOT EXISTS idx_chatmsg_session ON chat_messages (session_id);