"""
Shared test fixtures — uses a test_xp_system schema in Aiven PostgreSQL.
"""

import os
import sys
import psycopg2
import pytest
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

TEST_SCHEMA = "test_xp_system"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", "25840")),
    "dbname": os.getenv("DB_NAME", "defaultdb"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}


@pytest.fixture
def test_conn():
    """
    Create a test connection with a dedicated schema.
    Sets search_path so ALL queries (including from engine modules) use test tables.
    Cleans up after each test.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # Create and switch to test schema
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}")
    cur.execute(f"SET search_path TO {TEST_SCHEMA}")
    conn.commit()

    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL DEFAULT 'test_user',
            total_xp INTEGER NOT NULL DEFAULT 0,
            current_level INTEGER NOT NULL DEFAULT 1,
            streak_days INTEGER NOT NULL DEFAULT 0,
            last_active_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS xp_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            action_type VARCHAR(50) NOT NULL,
            xp_earned INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_ref_id VARCHAR(100),
            difficulty VARCHAR(20) DEFAULT 'beginner'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            badge_id SERIAL PRIMARY KEY,
            badge_name VARCHAR(100) UNIQUE NOT NULL,
            badge_description TEXT,
            badge_tier VARCHAR(30) NOT NULL,
            icon VARCHAR(50),
            criteria_json TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            badge_id INTEGER NOT NULL REFERENCES badges(badge_id) ON DELETE CASCADE,
            date_unlocked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lessons_completed INTEGER NOT NULL DEFAULT 0,
            quizzes_completed INTEGER NOT NULL DEFAULT 0,
            quizzes_correct INTEGER NOT NULL DEFAULT 0,
            challenges_completed INTEGER NOT NULL DEFAULT 0,
            simulation_score_avg REAL NOT NULL DEFAULT 0.0,
            total_lessons INTEGER NOT NULL DEFAULT 6,
            total_quizzes INTEGER NOT NULL DEFAULT 20,
            total_challenges INTEGER NOT NULL DEFAULT 10
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_xp_tracker (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            track_date DATE NOT NULL DEFAULT CURRENT_DATE,
            xp_earned_today INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, track_date)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS action_cooldowns (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            action_type VARCHAR(50) NOT NULL,
            source_ref_id VARCHAR(100) NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 1,
            first_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cooldown_date DATE NOT NULL DEFAULT CURRENT_DATE
        )
    """)
    conn.commit()

    # Clean all data for a fresh test
    cur.execute("DELETE FROM action_cooldowns")
    cur.execute("DELETE FROM daily_xp_tracker")
    cur.execute("DELETE FROM user_badges")
    cur.execute("DELETE FROM xp_logs")
    cur.execute("DELETE FROM progress")
    cur.execute("DELETE FROM badges")
    cur.execute("DELETE FROM users")
    conn.commit()

    # Create test user
    cur.execute(
        "INSERT INTO users (username, total_xp, current_level, streak_days) VALUES ('test_user', 0, 1, 0)"
    )
    cur.execute("SELECT id FROM users WHERE username = 'test_user'")
    user_id = cur.fetchone()[0]
    cur.execute("INSERT INTO progress (user_id) VALUES (%s)", (user_id,))
    conn.commit()
    cur.close()

    yield conn

    # Cleanup after test
    cleanup = conn.cursor()
    try:
        conn.rollback()
        cleanup.execute(f"SET search_path TO {TEST_SCHEMA}")
        cleanup.execute("DELETE FROM action_cooldowns")
        cleanup.execute("DELETE FROM daily_xp_tracker")
        cleanup.execute("DELETE FROM user_badges")
        cleanup.execute("DELETE FROM xp_logs")
        cleanup.execute("DELETE FROM progress")
        cleanup.execute("DELETE FROM badges")
        cleanup.execute("DELETE FROM users")
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cleanup.close()
        conn.close()


def get_test_user_id(conn):
    """Get the test user's ID."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = 'test_user'")
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None
