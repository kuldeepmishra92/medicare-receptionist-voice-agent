"""
Database Connection — SQLAlchemy Async Engine
Supports both SQLite (development) and PostgreSQL (production)
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings

# ── Build engine args based on DB type ───────────────────
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
}

# SQLite needs special config for async use
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

# ── Engine ────────────────────────────────────────────────
engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# ── Session Factory ───────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base Model ────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
