"""
Database connection manager for Aiven PostgreSQL.
Credentials loaded from environment variables via .env file.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from app_logger import logger

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", "25840")),
    "dbname": os.getenv("DB_NAME", "defaultdb"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}

_connection = None


def get_db():
    """Get or create a database connection singleton."""
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(**DB_CONFIG)
        _connection.autocommit = False
        logger.info("Database connection established")
    return _connection


def init_db():
    """Initialize database schema, run migrations, and seed data."""
    from .models import create_tables, seed_badges, seed_biomes
    conn = get_db()
    create_tables(conn)
    _run_migrations(conn)
    seed_badges(conn)
    seed_biomes(conn)
    conn.commit()
    logger.info("Database initialized successfully")


def _run_migrations(conn):
    """Add new columns to existing tables if they don't exist."""
    cur = conn.cursor()

    # Add email column to users if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'email'
            ) THEN
                ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE;
            END IF;
        END $$;
    """)

    # Add password_hash column to users if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_hash'
            ) THEN
                ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
            END IF;
        END $$;
    """)

    # Add last_login column to users if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'last_login'
            ) THEN
                ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
            END IF;
        END $$;
    """)

    # Add indexes on email and username if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_email') THEN
                CREATE INDEX idx_users_email ON users(email);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_username') THEN
                CREATE INDEX idx_users_username ON users(username);
            END IF;
        END $$;
    """)

    # Add xp_reward column to lessons if missing, then backfill
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'lessons' AND column_name = 'xp_reward'
            ) THEN
                ALTER TABLE lessons ADD COLUMN xp_reward INTEGER NOT NULL DEFAULT 50;
                -- Backfill based on difficulty
                UPDATE lessons SET xp_reward = 50  WHERE difficulty = 'beginner';
                UPDATE lessons SET xp_reward = 75  WHERE difficulty = 'intermediate';
                UPDATE lessons SET xp_reward = 100 WHERE difficulty = 'advanced';
            END IF;
        END $$;
    """)

    conn.commit()
    cur.close()
    logger.info("Database migrations completed")
