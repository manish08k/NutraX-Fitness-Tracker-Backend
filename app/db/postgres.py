from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings
from app.core.logger import logger


# Supabase uses PgBouncer on port 6543 for pooling — use NullPool for async
# Direct connection (port 5432) works fine with async engine pool
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,           # Keep small — Supabase free tier has 20 max connections
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,     # Recycle connections every 30 min
    pool_pre_ping=True,    # Check connection health before using
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Verify DB connection on startup. Migrations are handled by Alembic."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connected (Supabase)")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise


async def ping_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db() -> AsyncSession:
    """FastAPI dependency — one session per request, auto commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
