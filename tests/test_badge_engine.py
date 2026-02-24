"""
Unit tests for Badge Engine.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.badge_engine import check_badges, get_user_badges
from tests.conftest import get_test_user_id


def _seed_badges(conn):
    cur = conn.cursor()
    badges = [
        ("First Steps", "Complete first lesson", "🌱 Beginner", "SCHOOL",
         json.dumps({"type": "lessons_completed", "threshold": 1})),
        ("XP Achiever", "Reach 500 XP", "🌿 Growth", "STAR",
         json.dumps({"type": "total_xp", "threshold": 500})),
        ("Week Warrior", "7-day streak", "🌿 Growth", "LOCAL_FIRE_DEPARTMENT",
         json.dumps({"type": "streak_days", "threshold": 7})),
    ]
    for name, desc, tier, icon, criteria in badges:
        cur.execute(
            "INSERT INTO badges (badge_name, badge_description, badge_tier, icon, criteria_json) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (name, desc, tier, icon, criteria),
        )
    conn.commit()
    cur.close()


class TestBadgeUnlock:
    def test_first_lesson_badge(self, test_conn):
        _seed_badges(test_conn)
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE progress SET lessons_completed = 1 WHERE user_id = %s", (uid,))
        test_conn.commit()

        new_badges = check_badges(test_conn, uid)
        assert "First Steps" in [b["name"] for b in new_badges]
        cur.close()

    def test_xp_achiever_badge(self, test_conn):
        _seed_badges(test_conn)
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET total_xp = 500 WHERE id = %s", (uid,))
        test_conn.commit()

        new_badges = check_badges(test_conn, uid)
        assert "XP Achiever" in [b["name"] for b in new_badges]
        cur.close()

    def test_no_duplicate_badge(self, test_conn):
        _seed_badges(test_conn)
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE progress SET lessons_completed = 1 WHERE user_id = %s", (uid,))
        test_conn.commit()

        first = check_badges(test_conn, uid)
        second = check_badges(test_conn, uid)
        assert len(first) >= 1
        assert not any(b["name"] == "First Steps" for b in second)
        cur.close()

    def test_badge_in_user_badges(self, test_conn):
        _seed_badges(test_conn)
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE progress SET lessons_completed = 1 WHERE user_id = %s", (uid,))
        test_conn.commit()

        check_badges(test_conn, uid)
        user_badges = get_user_badges(test_conn, uid)
        assert "First Steps" in [b["name"] for b in user_badges]
        cur.close()

    def test_streak_badge_not_early(self, test_conn):
        _seed_badges(test_conn)
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET streak_days = 3 WHERE id = %s", (uid,))
        test_conn.commit()

        new_badges = check_badges(test_conn, uid)
        assert "Week Warrior" not in [b["name"] for b in new_badges]
        cur.close()
