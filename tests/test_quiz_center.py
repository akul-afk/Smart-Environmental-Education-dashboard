"""
Unit tests for QuizService and quiz logic.
Tests: random selection count, no duplicates, difficulty filter,
       XP calculation (perfect, high, zero scores).
"""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestQuizServiceXPCalculation:
    """Test XP calculation — no DB needed."""

    def setup_method(self):
        from services.quiz_service import QuizService
        self.svc = QuizService

    def test_xp_perfect_score(self):
        """100% correct → base + 80% bonus + perfect bonus."""
        result = self.svc.calculate_xp(10, 10, "mixed")
        assert result["correct"] == 10
        assert result["total"] == 10
        assert result["percentage"] == 100
        assert result["base_xp"] == 150      # 10 × 15
        assert result["bonus_xp"] == 40       # 80%+ bonus
        assert result["perfect_bonus"] == 40  # perfect bonus
        assert result["total_xp"] == 230      # 150 + 40 + 40

    def test_xp_high_score(self):
        """80% correct → base + 80% bonus, no perfect bonus."""
        result = self.svc.calculate_xp(8, 10, "mixed")
        assert result["percentage"] == 80
        assert result["base_xp"] == 120       # 8 × 15
        assert result["bonus_xp"] == 40
        assert result["perfect_bonus"] == 0
        assert result["total_xp"] == 160      # 120 + 40

    def test_xp_zero_score(self):
        """0 correct → 0 XP, no bonuses."""
        result = self.svc.calculate_xp(0, 10, "mixed")
        assert result["percentage"] == 0
        assert result["base_xp"] == 0
        assert result["bonus_xp"] == 0
        assert result["perfect_bonus"] == 0
        assert result["total_xp"] == 0

    def test_xp_below_80_percent(self):
        """79% → no 80% bonus."""
        result = self.svc.calculate_xp(7, 10, "mixed")
        assert result["percentage"] == 70
        assert result["bonus_xp"] == 0
        assert result["total_xp"] == 105      # 7 × 15

    def test_xp_challenge_multiplier(self):
        """Challenge mode applies 1.5× multiplier."""
        result = self.svc.calculate_xp(20, 20, "challenge")
        base = 300      # 20 × 15
        bonus = 40      # 80%+ bonus
        perfect = 40    # perfect bonus
        expected = int((base + bonus + perfect) * 1.5)
        assert result["total_xp"] == expected  # 570
        assert result["multiplier"] == 1.5

    def test_xp_challenge_zero(self):
        """Challenge mode with 0 correct → still 0."""
        result = self.svc.calculate_xp(0, 20, "challenge")
        assert result["total_xp"] == 0

    def test_xp_empty_quiz(self):
        """Edge case: 0-question quiz."""
        result = self.svc.calculate_xp(0, 0, "mixed")
        assert result["percentage"] == 0
        assert result["total_xp"] == 0


class TestQuizServiceAnswerValidation:
    """Test server-side answer validation."""

    def setup_method(self):
        from services.quiz_service import QuizService
        self.svc = QuizService

    def test_correct_answer(self):
        q = {
            "question_text": "Test?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 2,
            "explanation": "Because C is correct.",
        }
        result = self.svc.validate_answer(q, 2)
        assert result["is_correct"] is True
        assert result["correct_index"] == 2
        assert result["correct_answer"] == "C"
        assert result["explanation"] == "Because C is correct."

    def test_incorrect_answer(self):
        q = {
            "question_text": "Test?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "A is correct.",
        }
        result = self.svc.validate_answer(q, 3)
        assert result["is_correct"] is False
        assert result["correct_answer"] == "A"


class TestQuizServiceDBQueries:
    """Tests that require a live DB connection.
    These test the actual SQL queries and data integrity.
    """

    @pytest.fixture(autouse=True)
    def _db_setup(self):
        """Ensure DB is initialized before tests."""
        try:
            from database.db_connection import init_db
            init_db()
            self._has_db = True
        except Exception:
            self._has_db = False

    def test_random_selection_count(self):
        """fetch_questions returns exactly the requested number."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        questions = QuizService.fetch_questions("mixed")
        assert len(questions) == 10

    def test_easy_mode_returns_beginner_only(self):
        """Easy mode should only return beginner difficulty."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        questions = QuizService.fetch_questions("easy")
        for q in questions:
            assert q["difficulty"] == "beginner", \
                f"Got {q['difficulty']} in easy mode: {q['question_slug']}"

    def test_challenge_count(self):
        """Challenge mode returns 20 questions."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        questions = QuizService.fetch_questions("challenge")
        assert len(questions) == 20

    def test_no_duplicates_in_session(self):
        """All returned questions should have unique slugs."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        questions = QuizService.fetch_questions("mixed")
        slugs = [q["question_slug"] for q in questions]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_question_structure(self):
        """Each question should have required fields."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        questions = QuizService.fetch_questions("mixed")
        required = {"question_slug", "question_text", "options",
                     "correct_index", "explanation", "topic_tag", "difficulty"}
        for q in questions:
            assert required.issubset(set(q.keys())), \
                f"Missing keys in {q.get('question_slug', 'unknown')}"
            assert isinstance(q["options"], list)
            assert len(q["options"]) >= 2
            assert isinstance(q["correct_index"], int)

    def test_exclude_slugs(self):
        """Excluded slugs should not appear in results."""
        if not self._has_db:
            pytest.skip("No DB connection")

        from services.quiz_service import QuizService
        # First fetch
        q1 = QuizService.fetch_questions("mixed")
        exclude = [q["question_slug"] for q in q1[:3]]

        # Second fetch excluding first 3
        q2 = QuizService.fetch_questions("mixed", exclude_slugs=exclude)
        q2_slugs = {q["question_slug"] for q in q2}

        for slug in exclude:
            assert slug not in q2_slugs, f"Excluded slug {slug} still present"
