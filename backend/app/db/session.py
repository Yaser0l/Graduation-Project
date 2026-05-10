from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings



# Create async engine for PostgreSQL
# Example: postgresql+asyncpg://user:pass@host:port/db
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

# Create session factory
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency to get database session
async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    """Read schema.sql and create all tables if they don't exist yet.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    statements = []
    for chunk in sql.split(";"):
        # Drop comment-only lines and blank lines from the top of each chunk,
        # then keep whatever real SQL remains.
        lines = chunk.splitlines()
        sql_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith("--")
        ]
        stmt = "\n".join(sql_lines).strip()
        if stmt:
            statements.append(stmt)

    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))

    print(f"[DB] Schema initialised — {len(statements)} statements executed.")
