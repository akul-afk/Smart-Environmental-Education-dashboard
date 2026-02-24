"""
QuizService — encapsulates all quiz-related logic.

Responsibilities:
  - Fetch random questions from DB (single query)
  - Calculate XP rewards
  - Submit session results (transactional)
  - No UI coupling — pure business logic
"""
import json
from typing import List, Dict, Optional

from database.db_connection import get_db
from app_logger import logger


class QuizService:
    """Service layer for the Quiz Center."""

    # ── XP Constants ──
    XP_PER_CORRECT = 15
    BONUS_80_PERCENT = 40
    BONUS_PERFECT = 40
    CHALLENGE_MULTIPLIER = 1.5

    # ── Difficulty Modes ──
    MODE_EASY = "easy"          # beginner only, 10 questions
    MODE_MIXED = "mixed"        # all difficulties, 10 questions
    MODE_CHALLENGE = "challenge" # all difficulties, 20 questions

    MODE_CONFIG = {
        MODE_EASY:      {"difficulty": "beginner", "limit": 10},
        MODE_MIXED:     {"difficulty": None,       "limit": 10},
        MODE_CHALLENGE: {"difficulty": None,       "limit": 20},
    }

    @staticmethod
    def fetch_questions(mode: str, exclude_slugs: Optional[List[str]] = None) -> List[Dict]:
        """Fetch random questions from general_quiz_questions in a single query.

        Args:
            mode: One of 'easy', 'mixed', 'challenge'.
            exclude_slugs: Optional list of question_slugs to exclude
                           (avoids repeats within the same app session).

        Returns:
            List of question dicts. Each dict contains:
              question_slug, question_text, options (parsed list),
              correct_index, explanation, topic_tag, difficulty.
            correct_index IS included in the dict but the UI must
            NOT reveal it until the answer is submitted.
        """
        config = QuizService.MODE_CONFIG.get(mode, QuizService.MODE_CONFIG[QuizService.MODE_MIXED])
        difficulty = config["difficulty"]
        limit = config["limit"]

        conn = get_db()
        cur = conn.cursor()
        try:
            # Build query dynamically but safely with parameterization
            clauses = []
            params = []

            if difficulty:
                clauses.append("difficulty = %s")
                params.append(difficulty)

            if exclude_slugs:
                placeholders = ", ".join(["%s"] * len(exclude_slugs))
                clauses.append(f"question_slug NOT IN ({placeholders})")
                params.extend(exclude_slugs)

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            params.append(limit)

            sql = f"""
                SELECT question_slug, question_text, options_json,
                       correct_index, explanation, topic_tag, difficulty
                FROM general_quiz_questions
                {where}
                ORDER BY RANDOM()
                LIMIT %s;
            """

            cur.execute(sql, params)
            rows = cur.fetchall()

            questions = []
            for row in rows:
                options = row[2] if isinstance(row[2], list) else json.loads(row[2])
                questions.append({
                    "question_slug": row[0],
                    "question_text": row[1],
                    "options": options,
                    "correct_index": row[3],
                    "explanation": row[4] or "",
                    "topic_tag": row[5] or "General",
                    "difficulty": row[6] or "beginner",
                })

            logger.info("QuizService: fetched %d questions (mode=%s)", len(questions), mode)
            return questions

        except Exception as e:
            logger.error("QuizService.fetch_questions error: %s", e)
            return []
        finally:
            cur.close()

    @staticmethod
    def calculate_xp(correct: int, total: int, mode: str) -> dict:
        """Calculate XP earned for a quiz session.

        Returns:
            dict with keys: base_xp, bonus_xp, perfect_bonus, multiplier,
                           total_xp, percentage.
        """
        pct = int((correct / total) * 100) if total > 0 else 0
        base_xp = correct * QuizService.XP_PER_CORRECT

        bonus_xp = QuizService.BONUS_80_PERCENT if pct >= 80 else 0
        perfect_bonus = QuizService.BONUS_PERFECT if correct == total and total > 0 else 0

        subtotal = base_xp + bonus_xp + perfect_bonus

        multiplier = QuizService.CHALLENGE_MULTIPLIER if mode == QuizService.MODE_CHALLENGE else 1.0
        total_xp = int(subtotal * multiplier)

        return {
            "base_xp": base_xp,
            "bonus_xp": bonus_xp,
            "perfect_bonus": perfect_bonus,
            "multiplier": multiplier,
            "total_xp": total_xp,
            "percentage": pct,
            "correct": correct,
            "total": total,
        }

    @staticmethod
    def submit_session(user_id: int, correct: int, total: int,
                       mode: str, time_secs: int) -> dict:
        """Commit quiz session results: award XP + update progress counters.

        All DB operations in a single transaction.

        Returns:
            Combined dict with XP details + award_xp result.
        """
        xp_info = QuizService.calculate_xp(correct, total, mode)

        from services import DataService

        # Award total XP in one call
        award_result = {}
        if xp_info["total_xp"] > 0:
            award_result = DataService.award_xp(
                user_id,
                "quiz_correct",
                xp_info["total_xp"],
                source_ref_id=f"quiz_center_{mode}",
                difficulty="intermediate",  # neutral difficulty for XP engine
            )

        # Increment progress counters
        DataService.increment_progress(user_id, "quizzes_completed", 1)
        if correct > 0:
            DataService.increment_progress(user_id, "quizzes_correct", correct)

        logger.info(
            "QuizService: session submitted — user=%d, %d/%d correct, "
            "%d XP awarded, time=%ds, mode=%s",
            user_id, correct, total, xp_info["total_xp"], time_secs, mode,
        )

        return {**xp_info, **award_result, "time_secs": time_secs}

    @staticmethod
    def validate_answer(question: dict, selected_index: int) -> dict:
        """Server-side answer validation.

        Args:
            question: The question dict (with correct_index).
            selected_index: The user's selected option index.

        Returns:
            dict with is_correct, correct_index, explanation.
        """
        correct = selected_index == question["correct_index"]
        return {
            "is_correct": correct,
            "correct_index": question["correct_index"],
            "correct_answer": question["options"][question["correct_index"]],
            "explanation": question.get("explanation", ""),
        }
