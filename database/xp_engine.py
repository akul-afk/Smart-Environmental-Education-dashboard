"""
XP Engine — Core XP calculation, awarding, and querying.
"""

import math
from datetime import datetime


# Difficulty multipliers
DIFFICULTY_MULTIPLIERS = {
    "beginner": 1.0,
    "intermediate": 1.5,
    "advanced": 2.0,
}

# Streak bonus thresholds
STREAK_BONUSES = [
    (30, 1.5),
    (7, 1.2),
    (3, 1.1),
]


def calculate_xp(base_xp, difficulty="beginner", streak_days=0):
    """
    Calculate final XP using formula:
    Final XP = Base × Difficulty Multiplier × Streak Bonus

    Args:
        base_xp: Base XP value for the action
        difficulty: 'beginner', 'intermediate', or 'advanced'
        streak_days: Current streak day count

    Returns:
        int: Calculated XP (rounded down)
    """
    diff_mult = DIFFICULTY_MULTIPLIERS.get(difficulty.lower(), 1.0)

    streak_bonus = 1.0
    for threshold, bonus in STREAK_BONUSES:
        if streak_days >= threshold:
            streak_bonus = bonus
            break

    return int(math.floor(base_xp * diff_mult * streak_bonus))


def award_xp(conn, user_id, action_type, base_xp, source_ref_id=None, difficulty="beginner"):
    """
    Award XP to a user with full pipeline:
    1. Check abuse limits
    2. Calculate final XP
    3. Log to xp_logs
    4. Update daily tracker
    5. Update user total
    6. Check level up
    7. Check badges

    Returns:
        dict: {xp_earned, total_xp, level, leveled_up, new_badges, capped, streak_days}
    """
    from .abuse_prevention import check_abuse, update_daily_tracker
    from .level_engine import check_level_up
    from .badge_engine import check_badges
    from .streak_engine import update_streak

    cur = conn.cursor()

    # Update streak first
    update_streak(conn, user_id)

    # Get user info
    cur.execute("SELECT total_xp, current_level, streak_days FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        return {"xp_earned": 0, "error": "User not found"}

    current_xp, current_level, streak_days = row

    # Check abuse limits
    abuse_result = check_abuse(conn, user_id, action_type, source_ref_id)
    if not abuse_result["allowed"]:
        cur.close()
        return {
            "xp_earned": 0,
            "total_xp": current_xp,
            "level": current_level,
            "leveled_up": False,
            "new_badges": [],
            "capped": True,
            "reason": abuse_result["reason"],
            "streak_days": streak_days,
        }

    # Calculate XP
    final_xp = calculate_xp(base_xp, difficulty, streak_days)

    # Check daily cap (500 XP/day)
    cur.execute(
        "SELECT xp_earned_today FROM daily_xp_tracker WHERE user_id = %s AND track_date = CURRENT_DATE",
        (user_id,),
    )
    daily_row = cur.fetchone()
    daily_earned = daily_row[0] if daily_row else 0
    remaining_cap = max(0, 500 - daily_earned)

    if remaining_cap <= 0:
        cur.close()
        return {
            "xp_earned": 0,
            "total_xp": current_xp,
            "level": current_level,
            "leveled_up": False,
            "new_badges": [],
            "capped": True,
            "reason": "Daily XP cap (500) reached",
            "streak_days": streak_days,
        }

    # Cap the XP if needed
    actual_xp = min(final_xp, remaining_cap)

    # Log XP
    cur.execute(
        """
        INSERT INTO xp_logs (user_id, action_type, xp_earned, source_ref_id, difficulty)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, action_type, actual_xp, source_ref_id, difficulty),
    )

    # Update daily tracker
    update_daily_tracker(conn, user_id, actual_xp)

    # Update user total
    new_total = current_xp + actual_xp
    cur.execute("UPDATE users SET total_xp = %s WHERE id = %s", (new_total, user_id))

    conn.commit()

    # Check level up
    new_level, leveled_up = check_level_up(conn, user_id)

    # Check badges
    new_badges = check_badges(conn, user_id)

    cur.close()

    return {
        "xp_earned": actual_xp,
        "total_xp": new_total,
        "level": new_level,
        "leveled_up": leveled_up,
        "new_badges": new_badges,
        "capped": actual_xp < final_xp,
        "reason": None,
        "streak_days": streak_days,
    }


def get_user_stats(conn, user_id):
    """Get full user stats for display."""
    cur = conn.cursor()
    cur.execute(
        "SELECT username, total_xp, current_level, streak_days, last_active_date FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if row is None:
        cur.close()
        return None

    from .level_engine import xp_for_level

    username, total_xp, level, streak_days, last_active = row
    next_level_xp = xp_for_level(level + 1)
    current_level_xp = xp_for_level(level)
    xp_in_level = total_xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    progress_pct = min(100, int((xp_in_level / max(1, xp_needed)) * 100))

    # Daily XP
    cur.execute(
        "SELECT xp_earned_today FROM daily_xp_tracker WHERE user_id = %s AND track_date = CURRENT_DATE",
        (user_id,),
    )
    daily_row = cur.fetchone()
    daily_xp = daily_row[0] if daily_row else 0

    cur.close()

    return {
        "username": username,
        "total_xp": total_xp,
        "level": level,
        "streak_days": streak_days,
        "last_active": last_active,
        "next_level_xp": next_level_xp,
        "current_level_xp": current_level_xp,
        "xp_in_level": xp_in_level,
        "xp_needed": xp_needed,
        "progress_pct": progress_pct,
        "daily_xp": daily_xp,
        "daily_cap": 500,
    }


def get_xp_history(conn, user_id, limit=30):
    """Get recent XP earning history."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT action_type, xp_earned, timestamp, source_ref_id, difficulty
        FROM xp_logs
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "action_type": r[0],
            "xp_earned": r[1],
            "timestamp": r[2],
            "source_ref_id": r[3],
            "difficulty": r[4],
        }
        for r in rows
    ]


def get_daily_xp_series(conn, user_id, days=14):
    """Get daily XP totals for chart display."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT track_date, xp_earned_today
        FROM daily_xp_tracker
        WHERE user_id = %s
        ORDER BY track_date DESC
        LIMIT %s
        """,
        (user_id, days),
    )
    rows = cur.fetchall()
    cur.close()
    return [(str(r[0]), r[1]) for r in reversed(rows)]
