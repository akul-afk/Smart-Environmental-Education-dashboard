"""
Streak Engine — Daily streak tracking and bonus calculation.
"""

from datetime import date, timedelta


def update_streak(conn, user_id):
    """
    Update user streak based on last_active_date.
    
    Rules:
    - Same day: no change
    - Consecutive day: increment streak
    - Missed day(s): reset to 1
    
    Returns:
        int: current streak_days after update
    """
    cur = conn.cursor()
    cur.execute("SELECT streak_days, last_active_date FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        return 0

    streak_days, last_active = row
    today = date.today()

    if last_active is None:
        # First ever activity
        new_streak = 1
    elif last_active == today:
        # Already active today
        cur.close()
        return streak_days
    elif last_active == today - timedelta(days=1):
        # Consecutive day
        new_streak = streak_days + 1
    else:
        # Missed one or more days
        new_streak = 1

    cur.execute(
        "UPDATE users SET streak_days = %s, last_active_date = %s WHERE id = %s",
        (new_streak, today, user_id),
    )
    conn.commit()
    cur.close()
    return new_streak


def get_streak_bonus_label(streak_days):
    """Get a human-readable streak bonus label."""
    if streak_days >= 30:
        return "🔥 1.5× Streak Bonus (30+ days!)"
    elif streak_days >= 7:
        return "🔥 1.2× Streak Bonus (7+ days!)"
    elif streak_days >= 3:
        return "🔥 1.1× Streak Bonus (3+ days)"
    else:
        return ""
