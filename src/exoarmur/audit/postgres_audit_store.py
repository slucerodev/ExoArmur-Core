"""
Postgres Audit Store - Persistent audit storage with schema migration

Provides durable, queryable audit storage using PostgreSQL with:
- Schema versioning and migrations
- Deterministic record ordering
- Efficient correlation-based queries
- Archival and retention support
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import asdict

try:
    import asyncpg
    from asyncpg import Pool, Connection
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    Pool = None
    Connection = None

from exoarmur.clock import utc_now
from spec.contracts.models_v1 import AuditRecordV1

logger = logging.getLogger(__name__)

# Schema version for migrations
CURRENT_SCHEMA_VERSION = 1

# Schema creation SQL
SCHEMA_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Main audit records table
CREATE TABLE IF NOT EXISTS audit_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id VARCHAR(26) NOT NULL UNIQUE,  -- ULID format
    tenant_id VARCHAR(255) NOT NULL,
    correlation_id VARCHAR(255) NOT NULL,
    trace_id VARCHAR(255),
    event_kind VARCHAR(100) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    payload_ref JSONB NOT NULL,
    cell_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_records(correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_recorded_at ON audit_records(recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_idempotency ON audit_records(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_audit_event_kind ON audit_records(event_kind);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_tenant_correlation ON audit_records(tenant_id, correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_recorded ON audit_records(tenant_id, recorded_at DESC);

-- Archive table for retention management
CREATE TABLE IF NOT EXISTS audit_records_archive (
    id UUID PRIMARY KEY,
    record_id VARCHAR(26) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    correlation_id VARCHAR(255) NOT NULL,
    event_kind VARCHAR(100) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload_ref JSONB NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archive_reason VARCHAR(50) DEFAULT 'retention'
);

CREATE INDEX IF NOT EXISTS idx_archive_tenant ON audit_records_archive(tenant_id);
CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON audit_records_archive(archived_at);
"""


class PostgresAuditStore:
    """PostgreSQL-based persistent audit store"""

    def __init__(self, dsn: Optional[str] = None, pool: Optional[Pool] = None):
        """
        Initialize Postgres audit store

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host/db")
            pool: Existing asyncpg pool (if already created)
        """
        if not POSTGRES_AVAILABLE:
            raise RuntimeError("asyncpg is required for PostgresAuditStore. Install with: pip install asyncpg")

        self.dsn = dsn or self._get_dsn_from_env()
        self._pool: Optional[Pool] = pool
        self._schema_initialized = False

    def _get_dsn_from_env(self) -> str:
        """Get connection string from environment variables"""
        import os
        host = os.getenv("EXOARMUR_POSTGRES_HOST", "localhost")
        port = os.getenv("EXOARMUR_POSTGRES_PORT", "5432")
        user = os.getenv("EXOARMUR_POSTGRES_USER", "exoarmur")
        password = os.getenv("EXOARMUR_POSTGRES_PASSWORD", "")
        db = os.getenv("EXOARMUR_POSTGRES_DB", "exoarmur_audit")

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return f"postgresql://{user}@{host}:{port}/{db}"

    async def _get_pool(self) -> Pool:
        """Get or create connection pool"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
        return self._pool

    async def initialize_schema(self) -> bool:
        """
        Initialize database schema with migration support

        Returns:
            True if schema initialized successfully
        """
        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                # Execute schema creation
                await conn.execute(SCHEMA_SQL)

                # Check/update schema version
                version_row = await conn.fetchrow(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )

                current_version = version_row['version'] if version_row else 0

                if current_version < CURRENT_SCHEMA_VERSION:
                    await self._run_migrations(conn, current_version)

                self._schema_initialized = True
                logger.info(f"Postgres audit store schema initialized (version {CURRENT_SCHEMA_VERSION})")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False

    async def _run_migrations(self, conn: Connection, from_version: int) -> None:
        """Run schema migrations from current version"""
        # Migration logic for future schema versions
        # Each migration should be idempotent

        if from_version < 1:
            # Initial schema is created by SCHEMA_SQL
            await conn.execute(
                "INSERT INTO schema_version (version) VALUES ($1)",
                CURRENT_SCHEMA_VERSION
            )
            logger.info(f"Applied initial schema version {CURRENT_SCHEMA_VERSION}")

        # Future migrations:
        # if from_version < 2:
        #     await conn.execute("ALTER TABLE audit_records ADD COLUMN ...")
        #     await conn.execute("INSERT INTO schema_version (version) VALUES (2)")

    async def store_record(self, record: AuditRecordV1) -> bool:
        """
        Store an audit record

        Args:
            record: AuditRecordV1 to store

        Returns:
            True if stored successfully
        """
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()

            # Convert payload_ref to JSON string
            payload_ref_json = json.dumps(record.payload_ref) if record.payload_ref else '{}'

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_records (
                        record_id, tenant_id, correlation_id, trace_id,
                        event_kind, recorded_at, idempotency_key, payload_ref, cell_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (idempotency_key) DO NOTHING
                """,
                    record.record_id,
                    record.tenant_id,
                    record.correlation_id,
                    record.trace_id,
                    record.event_kind,
                    record.recorded_at,
                    record.idempotency_key,
                    payload_ref_json,
                    record.cell_id
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store audit record: {e}")
            return False

    async def get_records_by_correlation(
        self,
        correlation_id: str,
        tenant_id: Optional[str] = None
    ) -> List[AuditRecordV1]:
        """
        Get audit records by correlation ID

        Args:
            correlation_id: Correlation ID to query
            tenant_id: Optional tenant filter

        Returns:
            List of matching AuditRecordV1
        """
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                if tenant_id:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE correlation_id = $1 AND tenant_id = $2
                        ORDER BY recorded_at ASC
                    """, correlation_id, tenant_id)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE correlation_id = $1
                        ORDER BY recorded_at ASC
                    """, correlation_id)

                return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get records: {e}")
            return []

    async def get_records_by_tenant(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditRecordV1]:
        """
        Get audit records for a tenant with optional time range

        Args:
            tenant_id: Tenant ID to query
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum records to return

        Returns:
            List of matching AuditRecordV1
        """
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                if start_time and end_time:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE tenant_id = $1
                        AND recorded_at BETWEEN $2 AND $3
                        ORDER BY recorded_at DESC
                        LIMIT $4
                    """, tenant_id, start_time, end_time, limit)
                elif start_time:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE tenant_id = $1 AND recorded_at >= $2
                        ORDER BY recorded_at DESC
                        LIMIT $3
                    """, tenant_id, start_time, limit)
                elif end_time:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE tenant_id = $1 AND recorded_at <= $2
                        ORDER BY recorded_at DESC
                        LIMIT $3
                    """, tenant_id, end_time, limit)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM audit_records
                        WHERE tenant_id = $1
                        ORDER BY recorded_at DESC
                        LIMIT $2
                    """, tenant_id, limit)

                return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get tenant records: {e}")
            return []

    async def check_idempotency(self, idempotency_key: str) -> bool:
        """
        Check if a record with given idempotency key exists

        Args:
            idempotency_key: Idempotency key to check

        Returns:
            True if record exists
        """
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM audit_records WHERE idempotency_key = $1",
                    idempotency_key
                )
                return row is not None

        except Exception as e:
            logger.error(f"Failed to check idempotency: {e}")
            return False

    async def archive_old_records(
        self,
        retention_days: int = 90,
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """
        Archive records older than retention period

        Args:
            retention_days: Days to retain before archiving
            batch_size: Records to process per batch

        Returns:
            Dict with archived and remaining counts
        """
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()
            cutoff_date = utc_now() - __import__('datetime').timedelta(days=retention_days)

            async with pool.acquire() as conn:
                # Move records to archive
                result = await conn.execute("""
                    WITH archived AS (
                        DELETE FROM audit_records
                        WHERE recorded_at < $1
                        RETURNING id, record_id, tenant_id, correlation_id,
                                  event_kind, recorded_at, payload_ref
                    )
                    INSERT INTO audit_records_archive (
                        id, record_id, tenant_id, correlation_id,
                        event_kind, recorded_at, payload_ref, archive_reason
                    )
                    SELECT id, record_id, tenant_id, correlation_id,
                           event_kind, recorded_at, payload_ref, 'retention'
                    FROM archived
                """, cutoff_date)

                # Get counts
                active_count = await conn.fetchval("SELECT COUNT(*) FROM audit_records")
                archive_count = await conn.fetchval("SELECT COUNT(*) FROM audit_records_archive")

                logger.info(f"Archived records older than {retention_days} days")
                return {
                    "archived_total": archive_count,
                    "active_remaining": active_count
                }

        except Exception as e:
            logger.error(f"Failed to archive records: {e}")
            return {"archived_total": 0, "active_remaining": 0}

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        if not self._schema_initialized:
            await self.initialize_schema()

        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                active_count = await conn.fetchval("SELECT COUNT(*) FROM audit_records")
                archive_count = await conn.fetchval("SELECT COUNT(*) FROM audit_records_archive")

                # Get tenant distribution
                tenant_rows = await conn.fetch("""
                    SELECT tenant_id, COUNT(*) as count
                    FROM audit_records
                    GROUP BY tenant_id
                    ORDER BY count DESC
                """)

                # Get event kind distribution
                kind_rows = await conn.fetch("""
                    SELECT event_kind, COUNT(*) as count
                    FROM audit_records
                    GROUP BY event_kind
                    ORDER BY count DESC
                """)

                return {
                    "active_records": active_count,
                    "archived_records": archive_count,
                    "total_records": active_count + archive_count,
                    "tenants": {row['tenant_id']: row['count'] for row in tenant_rows},
                    "event_kinds": {row['event_kind']: row['count'] for row in kind_rows},
                    "schema_version": CURRENT_SCHEMA_VERSION
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def _row_to_record(self, row: asyncpg.Record) -> AuditRecordV1:
        """Convert database row to AuditRecordV1"""
        from spec.contracts.models_v1 import PayloadRefV1

        payload_ref = row['payload_ref']
        if isinstance(payload_ref, str):
            payload_ref = json.loads(payload_ref)

        return AuditRecordV1(
            record_id=row['record_id'],
            tenant_id=row['tenant_id'],
            correlation_id=row['correlation_id'],
            trace_id=row['trace_id'],
            event_kind=row['event_kind'],
            recorded_at=row['recorded_at'],
            idempotency_key=row['idempotency_key'],
            payload_ref=PayloadRefV1(**payload_ref) if payload_ref else None,
            cell_id=row['cell_id']
        )

    async def close(self):
        """Close database pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Postgres audit store connection pool closed")


class PostgresAuditStoreSync:
    """Synchronous wrapper for PostgresAuditStore"""

    def __init__(self, dsn: Optional[str] = None):
        self._async_store = PostgresAuditStore(dsn)
        self._loop = None

    def _get_loop(self):
        """Get or create event loop"""
        import asyncio
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def initialize_schema(self) -> bool:
        """Initialize schema (sync wrapper)"""
        loop = self._get_loop()
        return loop.run_until_complete(self._async_store.initialize_schema())

    def store_record(self, record: AuditRecordV1) -> bool:
        """Store record (sync wrapper)"""
        loop = self._get_loop()
        return loop.run_until_complete(self._async_store.store_record(record))

    def get_records_by_correlation(self, correlation_id: str, tenant_id: Optional[str] = None) -> List[AuditRecordV1]:
        """Get records by correlation (sync wrapper)"""
        loop = self._get_loop()
        return loop.run_until_complete(self._async_store.get_records_by_correlation(correlation_id, tenant_id))

    def close(self):
        """Close connection (sync wrapper)"""
        loop = self._get_loop()
        return loop.run_until_complete(self._async_store.close())
