from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback para desarrollo local
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./homepets.db"

# Supabase/Render entregan la URL como postgres:// o postgresql:// -> forzar el driver asyncpg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

connect_args: dict = {}

if DATABASE_URL.startswith("postgresql+asyncpg://"):
    partes = urlsplit(DATABASE_URL)
    # asyncpg no acepta "sslmode" en la URL (es de psycopg2); se quita y se usa connect_args
    query = [(k, v) for k, v in parse_qsl(partes.query) if k not in ("sslmode", "pgbouncer")]
    DATABASE_URL = urlunsplit(partes._replace(query=urlencode(query)))

    host = (partes.hostname or "").lower()
    es_local = host in ("localhost", "127.0.0.1", "::1", "")
    if not es_local:
        # Supabase / producción: conexión cifrada obligatoria
        connect_args["ssl"] = "require"
        if partes.port == 6543:
            # Pooler de Supabase en modo transacción (PgBouncer): sin prepared statements cacheados
            connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
