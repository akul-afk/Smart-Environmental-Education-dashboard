"""
Integration test — end-to-end XP flow.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.xp_engine import award_xp
from database.level_engine import check_level_up, xp_for_level
from database.badge_engine import check_badges, get_user_badges
from database.progress_engine import increment_progress, get_progress
from tests.conftest import get_test_user_id


def _seed_test_badges(conn):
    cur = conn.cursor()
    badges = [
        ("First Steps", "Complete first lesson", "🌱 Beginner", "SCHOOL",
         json.dumps({"type": "lessons_completed", "threshold": 1})),
        ("Quiz Starter", "Pass first quiz", "🌱 Beginner", "QUIZ",
         json.dumps({"type": "quizzes_completed", "threshold": 1})),
    ]
    for name, desc, tier, icon, criteria in badges:
        cur.execute(
            "INSERT INTO badges (badge_name, badge_description, badge_tier, icon, criteria_json) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (name, desc, tier, icon, criteria),
        )
    conn.commit()
    cur.close()


class TestFullFlow:
    def test_lesson_complete_flow(self, test_conn):
        _seed_test_badges(test_conn)
        uid = get_test_user_id(test_conn)

        result = award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="int_climate")
        assert result["xp_earned"] == 50

        increment_progress(test_conn, uid, "lessons_completed")
        progress = get_progress(test_conn, uid)
        assert progress["lessons_completed"] == 1

        new_badges = check_badges(test_conn, uid)
        assert "First Steps" in [b["name"] for b in new_badges]

        # No duplicate
        assert not any(b["name"] == "First Steps" for b in check_badges(test_conn, uid))

    def test_quiz_flow(self, test_conn):
        _seed_test_badges(test_conn)
        uid = get_test_user_id(test_conn)

        result = award_xp(test_conn, uid, "quiz_correct", 15, source_ref_id="int_q1")
        assert result["xp_earned"] == 15

        increment_progress(test_conn, uid, "quizzes_completed")
        increment_progress(test_conn, uid, "quizzes_correct")

        new_badges = check_badges(test_conn, uid)
        assert "Quiz Starter" in [b["name"] for b in new_badges]
        assert len(get_user_badges(test_conn, uid)) >= 1

    def test_accumulation(self, test_conn):
        uid = get_test_user_id(test_conn)

        award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="int_l2")
        award_xp(test_conn, uid, "quiz_correct", 15, source_ref_id="int_q2")
        award_xp(test_conn, uid, "quiz_correct", 15, source_ref_id="int_q3")

        cur = test_conn.cursor()
        cur.execute("SELECT total_xp FROM users WHERE id = %s", (uid,))
        assert cur.fetchone()[0] == 80
        cur.execute("SELECT COUNT(*) FROM xp_logs WHERE user_id = %s", (uid,))
        assert cur.fetchone()[0] == 3
        cur.close()

    def test_level_up_through_earning(self, test_conn):
        uid = get_test_user_id(test_conn)
        threshold = xp_for_level(2)

        remaining = threshold
        i = 0
        while remaining > 0:
            amt = min(50, remaining)
            award_xp(test_conn, uid, "lesson_complete", amt, source_ref_id=f"int_lvl_{i}")
            remaining -= amt
            i += 1

        cur = test_conn.cursor()
        cur.execute("SELECT current_level FROM users WHERE id = %s", (uid,))
        assert cur.fetchone()[0] >= 2
        cur.close()
