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
    push_subscription JSONB       DEFAULT NULL,   -- Web Push subscription object
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
    last_oil_change_km INTEGER      DEFAULT NULL,
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

CREATE INDEX IF NOT EXISTS idx_chatmsg_session ON chat_messages (session_id);
