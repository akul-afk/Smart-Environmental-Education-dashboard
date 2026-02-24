"""
Unit tests for Level Engine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.level_engine import xp_for_level, level_from_xp, check_level_up
from tests.conftest import get_test_user_id


class TestXPThresholds:
    def test_level_1_is_zero(self):
        assert xp_for_level(1) == 0

    def test_level_2_is_100(self):
        assert xp_for_level(2) == 100

    def test_increasing_difficulty(self):
        for i in range(1, 10):
            diff_now = xp_for_level(i + 1) - xp_for_level(i)
            diff_next = xp_for_level(i + 2) - xp_for_level(i + 1)
            assert diff_next > diff_now


class TestLevelFromXP:
    def test_zero_xp_is_level_1(self):
        assert level_from_xp(0) == 1

    def test_99_xp_is_level_1(self):
        assert level_from_xp(99) == 1

    def test_exact_threshold_levels_up(self):
        assert level_from_xp(xp_for_level(2)) == 2

    def test_280_xp_level(self):
        assert level_from_xp(280) >= 2

    def test_high_xp(self):
        assert level_from_xp(10000) >= 5


class TestLevelUp:
    def test_level_up_detected(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        threshold = xp_for_level(2)
        cur.execute("UPDATE users SET total_xp = %s WHERE id = %s", (threshold, uid))
        test_conn.commit()

        new_level, did_level = check_level_up(test_conn, uid)
        assert new_level == 2
        assert did_level is True
        cur.close()

    def test_no_level_up(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET total_xp = 50, current_level = 1 WHERE id = %s", (uid,))
        test_conn.commit()

        new_level, did_level = check_level_up(test_conn, uid)
        assert new_level == 1
        assert did_level is False
        cur.close()

    def test_level_increases_only_once(self, test_conn):
        uid = get_test_user_id(test_conn)
        cur = test_conn.cursor()
        cur.execute("UPDATE users SET total_xp = %s WHERE id = %s", (xp_for_level(2), uid))
        test_conn.commit()

        _, did1 = check_level_up(test_conn, uid)
        _, did2 = check_level_up(test_conn, uid)
        assert did1 is True
        assert did2 is False
        cur.close()
