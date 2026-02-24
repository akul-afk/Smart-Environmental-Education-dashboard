"""
Level Engine — Non-linear leveling system.

XP thresholds: xp_for_level(n) = 100 × n^1.5  (cumulative)
"""

import math


def xp_for_level(level):
    """
    Calculate cumulative XP required to reach a given level.
    
    Level 1 → 100 XP
    Level 2 → 283 XP
    Level 3 → 520 XP
    Level 4 → 800 XP
    ...
    """
    if level <= 1:
        return 0
    total = 0
    for lvl in range(1, level):
        total += int(100 * math.pow(lvl, 1.5))
    return total


def level_from_xp(total_xp):
    """Determine level from total XP."""
    level = 1
    while xp_for_level(level + 1) <= total_xp:
        level += 1
    return level


def check_level_up(conn, user_id):
    """
    Recalculate user level from total XP and update DB if changed.
    
    Returns:
        (new_level, did_level_up)
    """
    cur = conn.cursor()
    cur.execute("SELECT total_xp, current_level FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        return (1, False)

    total_xp, current_level = row
    new_level = level_from_xp(total_xp)

    did_level_up = new_level > current_level

    if did_level_up:
        cur.execute("UPDATE users SET current_level = %s WHERE id = %s", (new_level, user_id))
        conn.commit()

    cur.close()
    return (new_level, did_level_up)
