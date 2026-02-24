"""
Tests for the biome model — seeding, retrieval, and idempotency.
"""

import os
import sys
import pytest
import psycopg2
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

TEST_SCHEMA = "test_biomes"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", "25840")),
    "dbname": os.getenv("DB_NAME", "defaultdb"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}


@pytest.fixture
def biome_conn():
    """Create a test connection with a dedicated schema for biome tests."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}")
    cur.execute(f"SET search_path TO {TEST_SCHEMA}")
    conn.commit()

    # Create biomes table in test schema
    cur.execute("""
        CREATE TABLE IF NOT EXISTS biomes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(50) UNIQUE NOT NULL,
            short_description TEXT,
            theme_color VARCHAR(10),
            icon_name VARCHAR(50),
            difficulty_level VARCHAR(20) DEFAULT 'beginner',
            estimated_minutes INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Clean any previous test data
    cur.execute("DELETE FROM biomes")
    conn.commit()
    cur.close()

    yield conn

    # Cleanup
    cur = conn.cursor()
    cur.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
    conn.commit()
    cur.close()
    conn.close()


class TestBiomeSeeding:
    """Test biome seed data insertion."""

    def test_seed_creates_four_biomes(self, biome_conn):
        """Seeding should insert exactly 4 biomes."""
        from database.models import seed_biomes

        seed_biomes(biome_conn)

        cur = biome_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM biomes")
        count = cur.fetchone()[0]
        cur.close()

        assert count == 4, f"Expected 4 biomes, got {count}"

    def test_seed_is_idempotent(self, biome_conn):
        """Running seed twice should still result in exactly 4 biomes."""
        from database.models import seed_biomes

        seed_biomes(biome_conn)
        seed_biomes(biome_conn)  # Run twice

        cur = biome_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM biomes")
        count = cur.fetchone()[0]
        cur.close()

        assert count == 4, f"Expected 4 biomes after double seed, got {count}"

    def test_biome_slugs(self, biome_conn):
        """All 4 expected slugs should be present."""
        from database.models import seed_biomes

        seed_biomes(biome_conn)

        cur = biome_conn.cursor()
        cur.execute("SELECT slug FROM biomes ORDER BY id")
        slugs = [row[0] for row in cur.fetchall()]
        cur.close()

        expected = ["blue_sphere", "green_lungs", "energy_grid", "circular_economy"]
        assert slugs == expected, f"Expected {expected}, got {slugs}"


class TestBiomeRetrieval:
    """Test biome retrieval via DataService-style queries."""

    def test_get_all_biomes_returns_four(self, biome_conn):
        """get_all_biomes should return a list of 4 dicts."""
        from database.models import seed_biomes
        import psycopg2.extras

        seed_biomes(biome_conn)

        cur = biome_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, name, slug, short_description, theme_color,
                   icon_name, difficulty_level, estimated_minutes
            FROM biomes ORDER BY id
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()

        assert len(rows) == 4
        assert rows[0]["name"] == "The Blue Sphere"
        assert rows[0]["theme_color"] == "#3B82F6"

    def test_get_biome_by_slug(self, biome_conn):
        """Fetching by slug should return the correct biome."""
        from database.models import seed_biomes
        import psycopg2.extras

        seed_biomes(biome_conn)

        cur = biome_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM biomes WHERE slug = %s", ("blue_sphere",))
        row = cur.fetchone()
        cur.close()

        assert row is not None
        assert row["name"] == "The Blue Sphere"
        assert row["theme_color"] == "#3B82F6"
        assert row["icon_name"] == "🌊"
        assert row["difficulty_level"] == "beginner"
        assert row["estimated_minutes"] == 25

    def test_get_biome_by_invalid_slug(self, biome_conn):
        """Fetching a non-existent slug should return None."""
        from database.models import seed_biomes
        import psycopg2.extras

        seed_biomes(biome_conn)

        cur = biome_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM biomes WHERE slug = %s", ("does_not_exist",))
        row = cur.fetchone()
        cur.close()

        assert row is None
