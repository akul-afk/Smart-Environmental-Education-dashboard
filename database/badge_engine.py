"""
Badge Engine — Badge criteria checking and awarding.
"""

import json


def check_badges(conn, user_id):
    """
    Check all badge criteria for a user and award any newly earned badges.

    Returns:
        list of dicts: newly unlocked badges [{name, description, tier, icon}]
    """
    cur = conn.cursor()

    # Get user stats
    cur.execute("SELECT total_xp, streak_days FROM users WHERE id = %s", (user_id,))
    user_row = cur.fetchone()
    if user_row is None:
        cur.close()
        return []
    total_xp, streak_days = user_row

    # Get progress stats
    cur.execute(
        "SELECT lessons_completed, quizzes_completed, quizzes_correct, challenges_completed, simulation_score_avg FROM progress WHERE user_id = %s",
        (user_id,),
    )
    prog_row = cur.fetchone()
    if prog_row is None:
        cur.close()
        return []
    lessons_completed, quizzes_completed, quizzes_correct, challenges_completed, simulation_score_avg = prog_row

    # Get already-earned badge IDs
    cur.execute("SELECT badge_id FROM user_badges WHERE user_id = %s", (user_id,))
    earned_ids = {r[0] for r in cur.fetchall()}

    # Get all badges
    cur.execute("SELECT badge_id, badge_name, badge_description, badge_tier, icon, criteria_json FROM badges")
    all_badges = cur.fetchall()

    newly_unlocked = []

    for badge_id, name, desc, tier, icon, criteria_json in all_badges:
        if badge_id in earned_ids:
            continue

        criteria = json.loads(criteria_json)
        ctype = criteria.get("type", "")
        threshold = criteria.get("threshold", 0)

        earned = False

        if ctype == "lessons_completed":
            earned = lessons_completed >= threshold
        elif ctype == "quizzes_completed":
            earned = quizzes_completed >= threshold
        elif ctype == "total_xp":
            earned = total_xp >= threshold
        elif ctype == "streak_days":
            earned = streak_days >= threshold
        elif ctype == "challenges_completed":
            earned = challenges_completed >= threshold
        elif ctype == "simulation_score_avg":
            earned = simulation_score_avg >= threshold
        elif ctype == "quiz_accuracy":
            if quizzes_completed >= threshold:
                accuracy = (quizzes_correct / max(1, quizzes_completed)) * 100
                min_accuracy = criteria.get("min_accuracy", 80)
                earned = accuracy >= min_accuracy

        if earned:
            try:
                cur.execute(
                    "INSERT INTO user_badges (user_id, badge_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user_id, badge_id),
                )
                conn.commit()
                newly_unlocked.append({
                    "name": name,
                    "description": desc,
                    "tier": tier,
                    "icon": icon,
                })
            except Exception:
                conn.rollback()

    cur.close()
    return newly_unlocked


def get_user_badges(conn, user_id):
    """Get all badges a user has earned."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.badge_name, b.badge_description, b.badge_tier, b.icon, ub.date_unlocked
        FROM user_badges ub
        JOIN badges b ON ub.badge_id = b.badge_id
        WHERE ub.user_id = %s
        ORDER BY ub.date_unlocked DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "name": r[0],
            "description": r[1],
            "tier": r[2],
            "icon": r[3],
            "date_unlocked": r[4],
        }
        for r in rows
    ]


def get_all_badges(conn):
    """Get all available badges."""
    cur = conn.cursor()
    cur.execute("SELECT badge_id, badge_name, badge_description, badge_tier, icon, criteria_json FROM badges ORDER BY badge_tier, badge_id")
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "badge_id": r[0],
            "name": r[1],
            "description": r[2],
            "tier": r[3],
            "icon": r[4],
            "criteria": json.loads(r[5]),
        }
        for r in rows
    ]


def get_next_badges(conn, user_id, limit=3):
    """Get the next badges closest to being unlocked."""
    cur = conn.cursor()
    
    # Get user stats
    cur.execute("SELECT total_xp, streak_days FROM users WHERE id = %s", (user_id,))
    user_row = cur.fetchone()
    if not user_row:
        cur.close()
        return []
    total_xp, streak_days = user_row
    
    cur.execute(
        "SELECT lessons_completed, quizzes_completed, quizzes_correct, challenges_completed, simulation_score_avg FROM progress WHERE user_id = %s",
        (user_id,),
    )
    prog_row = cur.fetchone()
    if not prog_row:
        cur.close()
        return []
    lessons, quizzes, correct, challenges, sim_avg = prog_row
    
    # Get already earned badge IDs
    cur.execute("SELECT badge_id FROM user_badges WHERE user_id = %s", (user_id,))
    earned_ids = {r[0] for r in cur.fetchall()}
    
    # Get remaining badges with progress
    cur.execute("SELECT badge_id, badge_name, badge_description, badge_tier, icon, criteria_json FROM badges")
    candidates = []
    for badge_id, name, desc, tier, icon, criteria_json in cur.fetchall():
        if badge_id in earned_ids:
            continue
        criteria = json.loads(criteria_json)
        ctype = criteria.get("type", "")
        threshold = criteria.get("threshold", 0)
        
        current_val = 0
        if ctype == "lessons_completed":
            current_val = lessons
        elif ctype == "quizzes_completed":
            current_val = quizzes
        elif ctype == "total_xp":
            current_val = total_xp
        elif ctype == "streak_days":
            current_val = streak_days
        elif ctype == "challenges_completed":
            current_val = challenges
        elif ctype == "simulation_score_avg":
            current_val = sim_avg
        
        progress_pct = min(100, int((current_val / max(1, threshold)) * 100))
        candidates.append({
            "name": name,
            "description": desc,
            "tier": tier,
            "icon": icon,
            "progress_pct": progress_pct,
            "current": current_val,
            "threshold": threshold,
        })
    
    cur.close()
    # Sort by closest to completion
    candidates.sort(key=lambda x: x["progress_pct"], reverse=True)
    return candidates[:limit]
