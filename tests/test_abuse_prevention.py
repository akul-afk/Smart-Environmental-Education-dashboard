"""
Unit tests for Abuse Prevention.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.abuse_prevention import check_abuse, update_daily_tracker, get_daily_xp
from database.xp_engine import award_xp
from tests.conftest import get_test_user_id


class TestDailyXPCap:
    def test_tracker_increments(self, test_conn):
        uid = get_test_user_id(test_conn)
        update_daily_tracker(test_conn, uid, 100)
        update_daily_tracker(test_conn, uid, 150)
        assert get_daily_xp(test_conn, uid) == 250

    def test_cap_limits_xp(self, test_conn):
        uid = get_test_user_id(test_conn)
        update_daily_tracker(test_conn, uid, 490)
        test_conn.commit()

        result = award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="cap1")
        assert result["xp_earned"] <= 10
        assert result["capped"] is True

    def test_cap_blocks_at_500(self, test_conn):
        uid = get_test_user_id(test_conn)
        update_daily_tracker(test_conn, uid, 500)
        test_conn.commit()

        result = award_xp(test_conn, uid, "lesson_complete", 50, source_ref_id="cap2")
        assert result["xp_earned"] == 0
        assert result["capped"] is True


class TestRepeatLimits:
    def test_first_attempt_allowed(self, test_conn):
        uid = get_test_user_id(test_conn)
        assert check_abuse(test_conn, uid, "quiz_correct", "rq_1")["allowed"] is True

    def test_third_attempt_allowed(self, test_conn):
        uid = get_test_user_id(test_conn)
        check_abuse(test_conn, uid, "quiz_correct", "rq_2")
        check_abuse(test_conn, uid, "quiz_correct", "rq_2")
        assert check_abuse(test_conn, uid, "quiz_correct", "rq_2")["allowed"] is True

    def test_fourth_attempt_blocked(self, test_conn):
        uid = get_test_user_id(test_conn)
        for _ in range(3):
            check_abuse(test_conn, uid, "quiz_correct", "rq_3")
        assert check_abuse(test_conn, uid, "quiz_correct", "rq_3")["allowed"] is False

    def test_lesson_single_attempt(self, test_conn):
        uid = get_test_user_id(test_conn)
        assert check_abuse(test_conn, uid, "lesson_complete", "rl_1")["allowed"] is True
        assert check_abuse(test_conn, uid, "lesson_complete", "rl_1")["allowed"] is False

    def test_null_source_allowed(self, test_conn):
        uid = get_test_user_id(test_conn)
        assert check_abuse(test_conn, uid, "lesson_complete", None)["allowed"] is True
