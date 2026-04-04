from sqlalchemy import text

from app.db.session import engine


SCHEMA_STATEMENTS = [
    """
    CREATE EXTENSION IF NOT EXISTS pgcrypto
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vehicles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        vin VARCHAR(17) NOT NULL UNIQUE,
        make VARCHAR(100) NOT NULL,
        model VARCHAR(100) NOT NULL,
        year INTEGER NOT NULL,
        mileage INTEGER NOT NULL DEFAULT 0,
        last_oil_change_km INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS diagnostic_reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
        dtc_codes TEXT[] NOT NULL,
        mileage_at_fault INTEGER NOT NULL DEFAULT 0,
        llm_explanation TEXT,
        urgency VARCHAR(30) NOT NULL,
        estimated_cost_min INTEGER,
        estimated_cost_max INTEGER,
        resolved BOOLEAN NOT NULL DEFAULT FALSE,
        resolved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID NOT NULL REFERENCES diagnostic_reports(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (report_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vehicles_user_id ON vehicles(user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diagnostic_reports_vehicle_id ON diagnostic_reports(vehicle_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diagnostic_reports_resolved ON diagnostic_reports(resolved)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diagnostic_reports_created_at ON diagnostic_reports(created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at ASC)
    """,
]


async def init_db_schema() -> None:
    """Create required PostgreSQL extensions, tables, relations, and indexes."""
    async with engine.begin() as conn:
        for statement in SCHEMA_STATEMENTS:
            await conn.execute(text(statement))
