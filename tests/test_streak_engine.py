"""
Unit tests for Streak Engine.
"""

import sys
import os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.streak_engine import update_streak
from tests.conftest import get_test_user_id


class TestStreakLogic:
    def test_first_activity(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET last_active_date = NULL, streak_days = 0 WHERE id = %s", (uid,))
        test_conn.commit()
        assert update_streak(test_conn, uid) == 1
        cur.close()

    def test_same_day_no_change(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET last_active_date = %s, streak_days = 5 WHERE id = %s", (date.today(), uid))
        test_conn.commit()
        assert update_streak(test_conn, uid) == 5
        cur.close()

    def test_consecutive_day(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET last_active_date = %s, streak_days = 5 WHERE id = %s", (date.today() - timedelta(days=1), uid))
        test_conn.commit()
        assert update_streak(test_conn, uid) == 6
        cur.close()

    def test_missed_day_resets(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET last_active_date = %s, streak_days = 10 WHERE id = %s", (date.today() - timedelta(days=2), uid))
        test_conn.commit()
        assert update_streak(test_conn, uid) == 1
        cur.close()

    def test_long_gap_resets(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET last_active_date = %s, streak_days = 25 WHERE id = %s", (date.today() - timedelta(days=30), uid))
        test_conn.commit()
        assert update_streak(test_conn, uid) == 1
        cur.close()
