"""
Data Service — Central business logic layer.
All database interactions go through here, keeping UI code clean.
"""

from app_logger import logger


class DataService:
    """Provides a clean API for all data operations used by views."""

    @staticmethod
    def _get_conn():
        from database import get_db
        return get_db()

    # ── Authentication ──
    @staticmethod
    def login(email: str, password: str) -> dict:
        """Authenticate user. Returns {success, user_id, username} or {success, error}."""
        try:
            from database.auth import login_user
            return login_user(DataService._get_conn(), email, password)
        except Exception as e:
            logger.error("Login service error: %s", e)
            return {"success": False, "error": "Connection error. Please try again."}

    @staticmethod
    def register(username: str, email: str, password: str) -> dict:
        """Register new user. Returns {success, user_id, username} or {success, error}."""
        try:
            from database.auth import register_user
            return register_user(DataService._get_conn(), username, email, password)
        except Exception as e:
            logger.error("Registration service error: %s", e)
            return {"success": False, "error": "Connection error. Please try again."}

    # ── Home View Data ──
    @staticmethod
    def get_home_data(user_id: int) -> dict:
        """Get all data needed for the Home view."""
        try:
            conn = DataService._get_conn()
            from database.xp_engine import get_user_stats
            from database.badge_engine import get_next_badges
            from database.streak_engine import get_streak_bonus_label
            from database.progress_engine import get_progress

            stats = get_user_stats(conn, user_id)
            next_badges = get_next_badges(conn, user_id, limit=2)
            streak_label = get_streak_bonus_label(stats["streak_days"]) if stats else ""
            progress = get_progress(conn, user_id)
            return {
                "stats": stats,
                "next_badges": next_badges,
                "streak_label": streak_label,
                "progress": progress,
            }
        except Exception as e:
            logger.error("Home data load error: %s", e)
            return {"stats": None, "next_badges": [], "streak_label": "", "progress": None}

    # ── Progress View Data ──
    @staticmethod
    def get_progress_data(user_id: int) -> dict:
        """Get all data needed for the Progress view."""
        try:
            conn = DataService._get_conn()
            from database.xp_engine import get_user_stats, get_xp_history, get_daily_xp_series
            from database.badge_engine import get_user_badges, get_all_badges, get_next_badges
            from database.progress_engine import get_progress
            from database.streak_engine import get_streak_bonus_label

            stats = get_user_stats(conn, user_id)
            progress = get_progress(conn, user_id)
            earned_badges = get_user_badges(conn, user_id)
            all_badges = get_all_badges(conn)
            next_badges = get_next_badges(conn, user_id, limit=3)
            xp_history = get_xp_history(conn, user_id, limit=10)
            daily_series = get_daily_xp_series(conn, user_id, days=14)
            streak_label = get_streak_bonus_label(stats["streak_days"]) if stats else ""

            return {
                "stats": stats,
                "progress": progress,
                "earned_badges": earned_badges,
                "all_badges": all_badges,
                "next_badges": next_badges,
                "xp_history": xp_history,
                "daily_series": daily_series,
                "streak_label": streak_label,
            }
        except Exception as e:
            logger.error("Progress data load error: %s", e)
            return {
                "stats": None, "progress": None, "earned_badges": [],
                "all_badges": [], "next_badges": [], "xp_history": [],
                "daily_series": [], "streak_label": "",
            }

    # ── Simulator Data ──
    @staticmethod
    def get_simulator_stats(user_id: int) -> dict:
        """Get stats for the Simulator home screen."""
        try:
            conn = DataService._get_conn()
            from database.xp_engine import get_user_stats
            stats = get_user_stats(conn, user_id)
            return stats or {"total_xp": 0, "level": 1}
        except Exception as e:
            logger.error("Simulator stats load error: %s", e)
            return {"total_xp": 0, "level": 1}

    # ── XP Operations ──
    @staticmethod
    def award_xp(user_id: int, action_type: str, base_xp: int,
                 source_ref_id=None, difficulty="beginner") -> dict:
        """Award XP and return result dict."""
        try:
            conn = DataService._get_conn()
            from database.xp_engine import award_xp
            return award_xp(conn, user_id, action_type, base_xp,
                            source_ref_id=source_ref_id, difficulty=difficulty)
        except Exception as e:
            logger.error("Award XP error: %s", e)
            return {"xp_earned": 0, "error": str(e), "leveled_up": False, "new_badges": []}

    @staticmethod
    def increment_progress(user_id: int, field: str, amount: int = 1):
        """Increment a progress counter field."""
        try:
            conn = DataService._get_conn()
            from database.progress_engine import increment_progress
            increment_progress(conn, user_id, field, amount)
        except Exception as e:
            logger.error("Increment progress error: %s", e)

    @staticmethod
    def update_streak(user_id: int) -> int:
        """Update user streak and return current streak days."""
        try:
            conn = DataService._get_conn()
            from database.streak_engine import update_streak
            return update_streak(conn, user_id)
        except Exception as e:
            logger.error("Streak update error: %s", e)
            return 0

    # ── AI Insights ──
    @staticmethod
    def get_ai_insight(stats: dict, progress: dict, badges: list) -> str:
        """Get AI-powered motivational insight."""
        try:
            from database.ai_insights import get_ai_insight
            return get_ai_insight(stats, progress, badges)
        except Exception as e:
            logger.error("AI insight error: %s", e)
            return "🌍 Keep learning to protect our planet!"

    # ── Biomes ──
    @staticmethod
    def get_all_biomes() -> list:
        """Fetch all biomes from the database, ordered by id."""
        try:
            import psycopg2.extras
            conn = DataService._get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, name, slug, short_description, theme_color,
                       icon_name, difficulty_level, estimated_minutes, created_at
                FROM biomes
                ORDER BY id;
            """)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("Get all biomes error: %s", e)
            return []

    @staticmethod
    def get_biome_by_slug(slug: str) -> dict | None:
        """Fetch a single biome by its slug."""
        try:
            import psycopg2.extras
            conn = DataService._get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, name, slug, short_description, theme_color,
                       icon_name, difficulty_level, estimated_minutes, created_at
                FROM biomes
                WHERE slug = %s;
            """, (slug,))
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error("Get biome by slug error: %s", e)
            return None

    # ── Lessons ──
    @staticmethod
    def get_lessons_by_biome(biome_slug: str) -> list:
        """Fetch all lessons for a biome, ordered by id."""
        try:
            import psycopg2.extras
            conn = DataService._get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT l.id, l.biome_id, l.lesson_slug, l.title,
                       l.difficulty, l.estimated_minutes, l.xp_reward,
                       l.content_json, l.created_at
                FROM lessons l
                JOIN biomes b ON l.biome_id = b.id
                WHERE b.slug = %s
                ORDER BY l.id;
            """, (biome_slug,))
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("Get lessons by biome error: %s", e)
            return []

    @staticmethod
    def get_lesson_by_slug(lesson_slug: str) -> dict | None:
        """Fetch a single lesson with its quiz questions and key terms."""
        try:
            import psycopg2.extras
            conn = DataService._get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Fetch lesson
            cur.execute("""
                SELECT l.id, l.biome_id, l.lesson_slug, l.title,
                       l.difficulty, l.estimated_minutes, l.xp_reward,
                       l.content_json, l.created_at
                FROM lessons l
                WHERE l.lesson_slug = %s;
            """, (lesson_slug,))
            lesson = cur.fetchone()
            if lesson is None:
                cur.close()
                return None
            lesson = dict(lesson)

            # Fetch quiz questions
            cur.execute("""
                SELECT id, question_text, options_json, correct_index, explanation
                FROM quiz_questions
                WHERE lesson_id = %s
                ORDER BY id;
            """, (lesson["id"],))
            lesson["quiz"] = [dict(r) for r in cur.fetchall()]

            # Fetch key terms
            cur.execute("""
                SELECT term FROM key_terms
                WHERE lesson_id = %s
                ORDER BY id;
            """, (lesson["id"],))
            lesson["key_terms"] = [r["term"] for r in cur.fetchall()]

            cur.close()
            return lesson
        except Exception as e:
            logger.error("Get lesson by slug error: %s", e)
            return None

    @staticmethod
    def get_environmental_data():
        """Fetch all rows from environmental_country_stats, sorted by country name."""
        try:
            conn = DataService._get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT country_code, country_name, co2_per_capita,
                       renewable_percentage, forest_area_percentage, pm25, year
                FROM environmental_country_stats
                ORDER BY country_name;
            """)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
            return rows
        except Exception as e:
            logger.error("Get environmental data error: %s", e)
            return []

    @staticmethod
    def get_timeseries_data():
        """Load full time-series data from CSVs (cached after first call).

        Returns:
            dict: {factor_key: {country_code: [(year, value), ...]},
                   "_names": {country_code: country_name}}
        """
        try:
            from database.timeseries_loader import load_timeseries
            return load_timeseries()
        except Exception as e:
            logger.error("Get timeseries data error: %s", e)
            return {}
