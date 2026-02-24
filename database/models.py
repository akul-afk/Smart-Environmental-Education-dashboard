"""
Database models — PostgreSQL schema creation and seed data.
"""

import json


def create_tables(conn):
    """Create all tables if they don't exist."""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL DEFAULT 'eco_learner',
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255),
            total_xp INTEGER NOT NULL DEFAULT 0,
            current_level INTEGER NOT NULL DEFAULT 1,
            streak_days INTEGER NOT NULL DEFAULT 0,
            last_active_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
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
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            badge_id SERIAL PRIMARY KEY,
            badge_name VARCHAR(100) UNIQUE NOT NULL,
            badge_description TEXT,
            badge_tier VARCHAR(30) NOT NULL,
            icon VARCHAR(50),
            criteria_json TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            badge_id INTEGER NOT NULL REFERENCES badges(badge_id) ON DELETE CASCADE,
            date_unlocked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge_id)
        );
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
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_xp_tracker (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            track_date DATE NOT NULL DEFAULT CURRENT_DATE,
            xp_earned_today INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, track_date)
        );
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
        );
    """)

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            biome_id INTEGER NOT NULL REFERENCES biomes(id) ON DELETE CASCADE,
            lesson_slug VARCHAR(100) UNIQUE NOT NULL,
            title VARCHAR(255) NOT NULL,
            difficulty VARCHAR(20) DEFAULT 'beginner',
            estimated_minutes INTEGER DEFAULT 10,
            content_json JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            options_json JSONB NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS key_terms (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            term VARCHAR(200) NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS general_quiz_questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question_slug VARCHAR(150) UNIQUE NOT NULL,
            question_text TEXT NOT NULL,
            options_json JSONB NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation TEXT,
            topic_tag VARCHAR(50),
            difficulty VARCHAR(20) DEFAULT 'beginner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS environmental_country_stats (
            country_code CHAR(3) PRIMARY KEY,
            country_name VARCHAR(150) NOT NULL,
            co2_per_capita REAL,
            renewable_percentage REAL,
            forest_area_percentage REAL,
            pm25 REAL,
            year INTEGER NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create indexes for performance and random retrieval
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gqq_difficulty
            ON general_quiz_questions(difficulty);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gqq_topic_tag
            ON general_quiz_questions(topic_tag);
    """)

    conn.commit()
    cur.close()


BADGE_DEFINITIONS = [
    # Beginner Tier
    {
        "name": "First Steps",
        "desc": "Complete your first lesson",
        "tier": "🌱 Beginner",
        "icon": "SCHOOL",
        "criteria": {"type": "lessons_completed", "threshold": 1},
    },
    {
        "name": "Quiz Starter",
        "desc": "Pass your first quiz",
        "tier": "🌱 Beginner",
        "icon": "QUIZ",
        "criteria": {"type": "quizzes_completed", "threshold": 1},
    },
    {
        "name": "Curious Mind",
        "desc": "Complete 3 lessons",
        "tier": "🌱 Beginner",
        "icon": "LIGHTBULB",
        "criteria": {"type": "lessons_completed", "threshold": 3},
    },
    # Growth Tier
    {
        "name": "XP Achiever",
        "desc": "Reach 500 XP",
        "tier": "🌿 Growth",
        "icon": "STAR",
        "criteria": {"type": "total_xp", "threshold": 500},
    },
    {
        "name": "Week Warrior",
        "desc": "Maintain a 7-day streak",
        "tier": "🌿 Growth",
        "icon": "LOCAL_FIRE_DEPARTMENT",
        "criteria": {"type": "streak_days", "threshold": 7},
    },
    {
        "name": "Challenge Accepted",
        "desc": "Complete 3 sustainability challenges",
        "tier": "🌿 Growth",
        "icon": "EMOJI_EVENTS",
        "criteria": {"type": "challenges_completed", "threshold": 3},
    },
    {
        "name": "Knowledge Seeker",
        "desc": "Complete all 6 lessons",
        "tier": "🌿 Growth",
        "icon": "MENU_BOOK",
        "criteria": {"type": "lessons_completed", "threshold": 6},
    },
    # Impact Tier
    {
        "name": "XP Master",
        "desc": "Reach 2000 XP",
        "tier": "🌎 Impact",
        "icon": "MILITARY_TECH",
        "criteria": {"type": "total_xp", "threshold": 2000},
    },
    {
        "name": "Eco Simulator",
        "desc": "Achieve 90% average simulation score",
        "tier": "🌎 Impact",
        "icon": "PUBLIC",
        "criteria": {"type": "simulation_score_avg", "threshold": 90},
    },
    {
        "name": "Perfect Streak",
        "desc": "Maintain a 30-day streak",
        "tier": "🌎 Impact",
        "icon": "WHATSHOT",
        "criteria": {"type": "streak_days", "threshold": 30},
    },
    # Analyst Tier
    {
        "name": "Quiz Pro",
        "desc": "Complete 10 quizzes with 80%+ accuracy",
        "tier": "🧠 Analyst",
        "icon": "PSYCHOLOGY",
        "criteria": {"type": "quiz_accuracy", "threshold": 10, "min_accuracy": 80},
    },
    {
        "name": "Data Explorer",
        "desc": "Complete 15 quizzes",
        "tier": "🧠 Analyst",
        "icon": "ANALYTICS",
        "criteria": {"type": "quizzes_completed", "threshold": 15},
    },
]


def seed_badges(conn):
    """Insert badge definitions if they don't already exist."""
    cur = conn.cursor()
    for b in BADGE_DEFINITIONS:
        cur.execute(
            """
            INSERT INTO badges (badge_name, badge_description, badge_tier, icon, criteria_json)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (badge_name) DO NOTHING;
            """,
            (
                b["name"],
                b["desc"],
                b["tier"],
                b["icon"],
                json.dumps(b["criteria"]),
            ),
        )
    conn.commit()
    cur.close()


# ── Biome Definitions ──
BIOME_DEFINITIONS = [
    {
        "name": "The Blue Sphere",
        "slug": "blue_sphere",
        "short_description": "Dive into the world of oceans, freshwater systems, and water conservation. Explore marine ecosystems, pollution challenges, and sustainable water management.",
        "theme_color": "#3B82F6",
        "icon_name": "🌊",
        "difficulty_level": "beginner",
        "estimated_minutes": 25,
    },
    {
        "name": "The Green Lungs",
        "slug": "green_lungs",
        "short_description": "Explore forests, biodiversity, and land ecosystems. Learn about deforestation, carbon sinks, wildlife conservation, and sustainable agriculture.",
        "theme_color": "#22C55E",
        "icon_name": "🌳",
        "difficulty_level": "intermediate",
        "estimated_minutes": 35,
    },
    {
        "name": "The Energy Grid",
        "slug": "energy_grid",
        "short_description": "Master the future of energy — from fossil fuels to renewables. Understand solar, wind, nuclear power, and the global energy transition.",
        "theme_color": "#F59E0B",
        "icon_name": "⚡",
        "difficulty_level": "intermediate",
        "estimated_minutes": 40,
    },
    {
        "name": "The Circular Economy",
        "slug": "circular_economy",
        "short_description": "Rethink waste and recycling. Discover how circular design, upcycling, and zero-waste strategies are reshaping industry and daily life.",
        "theme_color": "#8B5CF6",
        "icon_name": "♻️",
        "difficulty_level": "advanced",
        "estimated_minutes": 45,
    },
]


def seed_biomes(conn):
    """Insert biome definitions if they don't already exist (idempotent)."""
    cur = conn.cursor()
    for b in BIOME_DEFINITIONS:
        cur.execute(
            """
            INSERT INTO biomes (name, slug, short_description, theme_color, icon_name,
                                difficulty_level, estimated_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO NOTHING;
            """,
            (
                b["name"], b["slug"], b["short_description"],
                b["theme_color"], b["icon_name"],
                b["difficulty_level"], b["estimated_minutes"],
            ),
        )
    conn.commit()
    cur.close()


def ensure_default_user(conn):
    """Create default local user if none exists."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = 'eco_learner'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, total_xp, current_level, streak_days) VALUES ('eco_learner', 0, 1, 0)"
        )
        # Create progress row
        cur.execute("SELECT id FROM users WHERE username = 'eco_learner'")
        user_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO progress (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user_id,),
        )
    conn.commit()
    cur.close()
