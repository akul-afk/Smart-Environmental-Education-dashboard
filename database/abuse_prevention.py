"""
Abuse Prevention — Rate limiting, daily caps, and repeat protection.
"""


def check_abuse(conn, user_id, action_type, source_ref_id=None):
    """
    Check if an XP action is allowed based on abuse prevention rules.
    
    Rules:
    - No XP for same quiz more than 3 times per day
    - No duplicate XP for re-watching same lesson within 24h
    - Daily XP cap checked separately in award_xp
    
    Returns:
        dict: {allowed: bool, reason: str or None}
    """
    if source_ref_id is None:
        return {"allowed": True, "reason": None}

    cur = conn.cursor()

    # Lifetime check for one-time XP rewards (like completing a lesson for the very first time)
    if action_type == "lesson_complete":
        cur.execute(
            """
            SELECT 1 FROM xp_logs
            WHERE user_id = %s AND action_type = %s AND source_ref_id = %s
            LIMIT 1
            """,
            (user_id, action_type, source_ref_id)
        )
        if cur.fetchone():
            cur.close()
            return {
                "allowed": False,
                "reason": "XP already claimed for this lesson",
            }

    # Check repeat limit for this specific action+source today
    cur.execute(
        """
        SELECT attempt_count FROM action_cooldowns
        WHERE user_id = %s AND action_type = %s AND source_ref_id = %s AND cooldown_date = CURRENT_DATE
        """,
        (user_id, action_type, source_ref_id),
    )
    row = cur.fetchone()

    max_attempts = _get_max_attempts(action_type)

    if row and row[0] >= max_attempts:
        cur.close()
        return {
            "allowed": False,
            "reason": f"Max {max_attempts} attempts per day for this action",
        }

    # Update or insert cooldown record
    if row:
        cur.execute(
            """
            UPDATE action_cooldowns
            SET attempt_count = attempt_count + 1, last_attempt = CURRENT_TIMESTAMP
            WHERE user_id = %s AND action_type = %s AND source_ref_id = %s AND cooldown_date = CURRENT_DATE
            """,
            (user_id, action_type, source_ref_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO action_cooldowns (user_id, action_type, source_ref_id, attempt_count, cooldown_date)
            VALUES (%s, %s, %s, 1, CURRENT_DATE)
            """,
            (user_id, action_type, source_ref_id),
        )

    conn.commit()
    cur.close()
    return {"allowed": True, "reason": None}


def _get_max_attempts(action_type):
    """Get max allowed attempts per day based on action type."""
    limits = {
        "quiz_attempt": 3,
        "quiz_correct": 3,
        "quiz_perfect": 1,
        "lesson_complete": 1,
        "lesson_watch": 1,
        "challenge_complete": 1,
        "simulation_play": 3,
        "carbon_calc": 2,
    }
    return limits.get(action_type, 5)


def update_daily_tracker(conn, user_id, xp_amount):
    """Update the daily XP tracker."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO daily_xp_tracker (user_id, track_date, xp_earned_today)
        VALUES (%s, CURRENT_DATE, %s)
        ON CONFLICT (user_id, track_date)
        DO UPDATE SET xp_earned_today = daily_xp_tracker.xp_earned_today + %s
        """,
        (user_id, xp_amount, xp_amount),
    )
    conn.commit()
    cur.close()


def get_daily_xp(conn, user_id):
    """Get XP earned today."""
    cur = conn.cursor()
    cur.execute(
        "SELECT xp_earned_today FROM daily_xp_tracker WHERE user_id = %s AND track_date = CURRENT_DATE",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else 0
