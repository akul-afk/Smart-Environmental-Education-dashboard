"""
AI Insights — Gemini-powered personalized learning insights.
API key loaded from environment variable.
"""

import os
from dotenv import load_dotenv

from app_logger import logger

# Load .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_ai_insight(user_stats, progress_data, badges_earned):
    """
    Generate a personalized AI insight using Gemini.

    Args:
        user_stats: dict from get_user_stats()
        progress_data: dict from get_progress()
        badges_earned: list of badge dicts

    Returns:
        str: Motivational insight message (1-2 sentences)
    """
    if not GEMINI_API_KEY:
        logger.warning("Gemini API key not configured, using fallback insight")
        return _get_fallback_insight(user_stats, progress_data)

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        badge_names = [b["name"] for b in badges_earned] if badges_earned else ["None yet"]

        prompt = f"""You are a friendly environmental education coach. Generate a SHORT, personalized motivational insight (1-2 sentences max) for a student based on their progress:

- Level: {user_stats.get('level', 1)}
- Total XP: {user_stats.get('total_xp', 0)}
- Streak: {user_stats.get('streak_days', 0)} days
- Lessons completed: {progress_data.get('lessons_completed', 0)}/{progress_data.get('total_lessons', 6)}
- Quizzes done: {progress_data.get('quizzes_completed', 0)}
- Challenges done: {progress_data.get('challenges_completed', 0)}
- Learning progress: {progress_data.get('learning_pct', 0)}%
- Badges earned: {', '.join(badge_names)}

Be encouraging, mention specific next steps, and use 1-2 emojis. Keep it under 30 words. Focus on environmental education motivation."""

        response = model.generate_content(prompt)
        logger.info("AI insight generated successfully")
        return response.text.strip()

    except Exception as e:
        logger.error("AI insight generation failed: %s", str(e))
        return _get_fallback_insight(user_stats, progress_data)


def _get_fallback_insight(user_stats, progress_data):
    """Provide a fallback insight when API is unavailable."""
    streak = user_stats.get("streak_days", 0)
    level = user_stats.get("level", 1)
    lessons = progress_data.get("lessons_completed", 0)

    if streak >= 7:
        return f"🔥 Amazing {streak}-day streak! You're a true eco-champion. Keep the momentum going!"
    elif level >= 3:
        return f"🌟 Level {level} and rising! Your environmental knowledge is growing fast."
    elif lessons >= 3:
        return f"📚 {lessons} lessons mastered! Try a quiz next to test what you've learned."
    elif lessons >= 1:
        return "🌱 Great start! Explore more topics to boost your XP and unlock badges."
    else:
        return "🌍 Welcome! Complete your first lesson to start earning XP and badges."
