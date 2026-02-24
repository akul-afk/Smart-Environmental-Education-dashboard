"""
Unit tests for XP Engine — XP calculation and awarding.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.xp_engine import calculate_xp, award_xp
from tests.conftest import get_test_user_id


class TestXPCalculation:
    """Test the XP calculation formula."""

    def test_basic_calculation(self):
        assert calculate_xp(50, "beginner", 0) == 50

    def test_difficulty_intermediate(self):
        assert calculate_xp(50, "intermediate", 0) == 75

    def test_difficulty_advanced(self):
        assert calculate_xp(50, "advanced", 0) == 100

    def test_streak_3_days(self):
        assert calculate_xp(50, "beginner", 3) == 55

    def test_streak_7_days(self):
        assert calculate_xp(50, "beginner", 7) == 60

    def test_streak_30_days(self):
        assert calculate_xp(50, "beginner", 30) == 75

    def test_full_formula_120(self):
        """50 × 2.0 × 1.2 = 120"""
        assert calculate_xp(50, "advanced", 7) == 120

    def test_full_formula_225(self):
        """75 × 2.0 × 1.5 = 225"""
        assert calculate_xp(75, "advanced", 30) == 225

    def test_zero_base(self):
        assert calculate_xp(0, "advanced", 30) == 0

    def test_unknown_difficulty(self):
        assert calculate_xp(100, "expert", 0) == 100


class TestXPAward:
    """Test XP awarding to DB."""

    def test_award_updates_total(self, test_conn):
        uid = get_test_user_id(test_conn)
        result = award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="t_lesson_1")
        assert result["xp_earned"] == 50
        assert result["total_xp"] == 50

        cur = test_conn.cursor()
        cur.execute("SELECT total_xp FROM users WHERE id = %s", (uid,))
        assert cur.fetchone()[0] == 50
        cur.close()

    def test_xp_log_created(self, test_conn):
        uid = get_test_user_id(test_conn)
        award_xp(test_conn, uid, "quiz_correct", 15, source_ref_id="t_quiz_1")

        cur = test_conn.cursor()
        cur.execute("SELECT action_type, xp_earned FROM xp_logs WHERE user_id = %s", (uid,))
        rows = cur.fetchall()
        assert any(r[0] == "quiz_correct" and r[1] == 15 for r in rows)
        cur.close()

    def test_cumulative_xp(self, test_conn):
        uid = get_test_user_id(test_conn)
        award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="t_la")
        award_xp(test_conn, uid, "quiz_correct", 15, source_ref_id="t_qa")

        cur = test_conn.cursor()
        cur.execute("SELECT total_xp FROM users WHERE id = %s", (uid,))
        assert cur.fetchone()[0] == 65
        cur.close()
