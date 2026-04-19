#!/usr/bin/env python3
"""
Initialize PostgreSQL schema for ExoArmur audit store

Usage:
    python scripts/init_postgres_schema.py [--dsn DSN]

Environment variables:
    EXOARMUR_POSTGRES_HOST      - Database host (default: localhost)
    EXOARMUR_POSTGRES_PORT      - Database port (default: 5432)
    EXOARMUR_POSTGRES_USER      - Database user (default: exoarmur)
    EXOARMUR_POSTGRES_PASSWORD  - Database password
    EXOARMUR_POSTGRES_DB        - Database name (default: exoarmur_audit)
"""

import asyncio
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def init_schema(dsn: str = None) -> bool:
    """Initialize the PostgreSQL schema"""
    try:
        from exoarmur.audit import PostgresAuditStore

        store = PostgresAuditStore(dsn=dsn)
        success = await store.initialize_schema()

        if success:
            # Get stats after initialization
            stats = await store.get_storage_stats()
            logger.info(f"Schema initialized successfully (version {stats.get('schema_version', 'unknown')})")
            logger.info(f"Current stats: {stats}")
        else:
            logger.error("Failed to initialize schema")

        await store.close()
        return success

    except ImportError as e:
        logger.error(f"Required dependencies not installed: {e}")
        logger.error("Install with: pip install asyncpg")
        return False
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Initialize ExoArmur PostgreSQL audit schema")
    parser.add_argument(
        "--dsn",
        help="PostgreSQL connection string (overrides environment variables)"
    )
    parser.add_argument(
        "--host",
        help="Database host (default: from EXOARMUR_POSTGRES_HOST or localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Database port (default: from EXOARMUR_POSTGRES_PORT or 5432)"
    )
    parser.add_argument(
        "--user",
        help="Database user (default: from EXOARMUR_POSTGRES_USER or exoarmur)"
    )
    parser.add_argument(
        "--password",
        help="Database password (default: from EXOARMUR_POSTGRES_PASSWORD)"
    )
    parser.add_argument(
        "--db",
        help="Database name (default: from EXOARMUR_POSTGRES_DB or exoarmur_audit)"
    )

    args = parser.parse_args()

    # Build DSN from individual args if provided
    if args.dsn:
        dsn = args.dsn
    elif any([args.host, args.port, args.user, args.password, args.db]):
        import os
        host = args.host or os.getenv("EXOARMUR_POSTGRES_HOST", "localhost")
        port = args.port or os.getenv("EXOARMUR_POSTGRES_PORT", "5432")
        user = args.user or os.getenv("EXOARMUR_POSTGRES_USER", "exoarmur")
        password = args.password or os.getenv("EXOARMUR_POSTGRES_PASSWORD", "")
        db = args.db or os.getenv("EXOARMUR_POSTGRES_DB", "exoarmur_audit")

        if password:
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        else:
            dsn = f"postgresql://{user}@{host}:{port}/{db}"
    else:
        dsn = None  # Will use environment variables or defaults

    success = asyncio.run(init_schema(dsn))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
