"""
PostgreSQL connection pool and schema bootstrap for the ExoArmur API layer.

DB is optional — if EXOARMUR_DATABASE_URL is not set, the API falls back to
in-memory stores.  When the URL is present, `init_db()` creates the schema
from migration files and returns a connection pool.
"""

import json
import os
from pathlib import Path
from typing import Optional

import asyncpg

POOL: Optional[asyncpg.Pool] = None

DEFAULT_DSN = "postgresql://exoarmur:exoarmur@localhost:5432/exoarmur"


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Per-connection setup: JSONB codec so repositories can pass dicts."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


def get_dsn() -> Optional[str]:
    return os.getenv("EXOARMUR_DATABASE_URL") or None


async def init_db(dsn: Optional[str] = None) -> Optional[asyncpg.Pool]:
    """Create pool, run migrations, return pool (or None if no DSN)."""
    global POOL
    url = dsn or get_dsn()
    if not url:
        return None

    POOL = await asyncpg.create_pool(
        url,
        min_size=int(os.getenv("EXOARMUR_DB_POOL_SIZE", "5")),
        max_size=int(os.getenv("EXOARMUR_DB_POOL_SIZE", "5")) * 2,
        init=_init_connection,
    )
    await _run_migrations()
    return POOL


async def close_db() -> None:
    global POOL
    if POOL is not None:
        await POOL.close()
        POOL = None


async def _run_migrations() -> None:
    if POOL is None:
        return
    migrations_dir = Path(__file__).with_suffix("").parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    async with POOL.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migration_log (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        for sql_file in sql_files:
            applied = await conn.fetchval(
                "SELECT 1 FROM _migration_log WHERE filename = $1",
                sql_file.name,
            )
            if applied:
                continue
            sql = sql_file.read_text()
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO _migration_log (filename) VALUES ($1)",
                sql_file.name,
            )


async def get_pool() -> Optional[asyncpg.Pool]:
    return POOL
