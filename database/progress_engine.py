"""
Progress Engine — 3-dimension progress tracking.
"""


def get_progress(conn, user_id):
    """
    Get user progress across 3 dimensions.
    
    Returns:
        dict with learning_pct, sustainability_pct, analytics_pct, raw counts, milestones
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT lessons_completed, quizzes_completed, quizzes_correct, challenges_completed,
               simulation_score_avg, total_lessons, total_quizzes, total_challenges
        FROM progress WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()

    if row is None:
        return {
            "learning_pct": 0,
            "sustainability_pct": 0,
            "analytics_pct": 0,
            "lessons_completed": 0,
            "quizzes_completed": 0,
            "quizzes_correct": 0,
            "challenges_completed": 0,
            "simulation_score_avg": 0,
            "milestones": [],
        }

    lessons, quizzes, correct, challenges, sim_avg, tot_lessons, tot_quizzes, tot_challenges = row

    learning_pct = min(100, int((lessons / max(1, tot_lessons)) * 100))
    sustainability_pct = min(100, int((challenges / max(1, tot_challenges)) * 100))
    analytics_pct = min(100, int((quizzes / max(1, tot_quizzes)) * 100))

    # Determine milestones
    milestones = []
    if lessons >= 1:
        milestones.append("🎓 First lesson completed")
    if lessons >= 3:
        milestones.append("📚 Halfway through lessons")
    if lessons >= tot_lessons:
        milestones.append("🏅 All lessons mastered!")
    if quizzes >= 1:
        milestones.append("📝 First quiz done")
    if quizzes >= 10:
        milestones.append("🧠 Quiz veteran (10+)")
    if challenges >= 1:
        milestones.append("🌿 First challenge completed")
    if challenges >= tot_challenges:
        milestones.append("🌍 All challenges conquered!")

    return {
        "learning_pct": learning_pct,
        "sustainability_pct": sustainability_pct,
        "analytics_pct": analytics_pct,
        "lessons_completed": lessons,
        "quizzes_completed": quizzes,
        "quizzes_correct": correct,
        "challenges_completed": challenges,
        "simulation_score_avg": sim_avg,
        "total_lessons": tot_lessons,
        "total_quizzes": tot_quizzes,
        "total_challenges": tot_challenges,
        "milestones": milestones,
    }


def increment_progress(conn, user_id, field, amount=1):
    """
    Increment a progress field.
    
    field: 'lessons_completed', 'quizzes_completed', 'quizzes_correct',
           'challenges_completed'
    """
    allowed_fields = {
        "lessons_completed",
        "quizzes_completed",
        "quizzes_correct",
        "challenges_completed",
    }
    if field not in allowed_fields:
        return

    cur = conn.cursor()
    cur.execute(
        f"UPDATE progress SET {field} = {field} + %s WHERE user_id = %s",
        (amount, user_id),
    )
    conn.commit()
    cur.close()


def update_simulation_score(conn, user_id, new_score):
    """Update simulation score average."""
    cur = conn.cursor()
    cur.execute(
        "SELECT simulation_score_avg, challenges_completed FROM progress WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if row:
        old_avg, count = row
        # Running average
        new_avg = ((old_avg * count) + new_score) / (count + 1) if count > 0 else new_score
        cur.execute(
            "UPDATE progress SET simulation_score_avg = %s WHERE user_id = %s",
            (new_avg, user_id),
        )
        conn.commit()
    cur.close()
