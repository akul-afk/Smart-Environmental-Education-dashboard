"""
Quiz Center — Dedicated quiz module with DB-backed questions.

Screens:
  1. Mode Selection (Easy / Mixed / Challenge)
  2. Question (progress bar, timer, 4 options)
  3. Answer Feedback (correct/incorrect, explanation, XP)
  4. Results Summary (score, time, XP, retry, dashboard)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea, QProgressBar,
    QSizePolicy, QSpacerItem, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from constants import COLORS
from app_logger import logger


# ── Background Workers ──

class _QuizLoadWorker(QThread):
    """Fetch questions from DB in a background thread."""
    finished = Signal(list)

    def __init__(self, mode, exclude_slugs=None):
        super().__init__()
        self.mode = mode
        self.exclude_slugs = exclude_slugs

    def run(self):
        from services import QuizService
        questions = QuizService.fetch_questions(self.mode, self.exclude_slugs)
        self.finished.emit(questions)


class _QuizSubmitWorker(QThread):
    """Submit quiz session results in a background thread."""
    finished = Signal(dict)

    def __init__(self, user_id, correct, total, mode, time_secs):
        super().__init__()
        self.user_id = user_id
        self.correct = correct
        self.total = total
        self.mode = mode
        self.time_secs = time_secs

    def run(self):
        from services import QuizService
        result = QuizService.submit_session(
            self.user_id, self.correct, self.total,
            self.mode, self.time_secs,
        )
        self.finished.emit(result)


# ── Main Widget ──

class QuizCenterWidget(QWidget):
    """Dedicated Quiz Center with difficulty modes, timer, and XP rewards."""

    def __init__(self, user_id=1, parent=None):
        super().__init__(parent)
        self.user_id = user_id

        # Session state
        self._questions = []
        self._current_idx = 0
        self._score = 0
        self._mode = "mixed"
        self._elapsed_secs = 0
        self._session_answered_slugs = []  # avoid repeats across retries

        # Workers (prevent GC)
        self._load_worker = None
        self._submit_worker = None

        # Timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        # Layout
        self._stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._show_mode_selection()

    # ── Helpers ──

    def _set_screen(self, widget):
        """Push a new screen onto the stack."""
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def _styled_btn(self, text, color, width=200, height=48, font_size=14):
        """Create a consistently styled button."""
        btn = QPushButton(text)
        btn.setFixedSize(width, height)
        btn.setFont(QFont("Segoe UI", font_size, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #FFFFFF;
                border: none; border-radius: 12px;
            }}
            QPushButton:hover {{ background-color: {color}cc; }}
        """)
        return btn

    def _tick(self):
        """Timer tick — update elapsed seconds and label."""
        self._elapsed_secs += 1
        if hasattr(self, '_timer_label') and self._timer_label:
            mins = self._elapsed_secs // 60
            secs = self._elapsed_secs % 60
            self._timer_label.setText(f"⏱ {mins:02d}:{secs:02d}")

    # ══════════════════════════════════════════════════════════
    # SCREEN 1 — Mode Selection
    # ══════════════════════════════════════════════════════════

    def _show_mode_selection(self):
        """Display the 3 mode cards."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(0)

        # Header
        title = QLabel("🧠 Quiz Center")
        title.setFont(QFont("Segoe UI", 30, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        sub = QLabel("Test your environmental knowledge — powered by 120 questions from the quiz bank")
        sub.setFont(QFont("Segoe UI", 13))
        sub.setStyleSheet(f"color: {COLORS['text_secondary']};")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        layout.addSpacerItem(QSpacerItem(0, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Mode cards
        modes = [
            ("🌱", "Easy Mode", "Beginner-level questions only",
             "10 questions", "easy", COLORS["primary"]),
            ("🌍", "Mixed Mode", "Random from all difficulty levels",
             "10 questions", "mixed", COLORS["secondary"]),
            ("⚡", "Challenge", "All difficulties, more questions, bonus XP!",
             "20 questions · 1.5× XP", "challenge", COLORS["tertiary"]),
        ]

        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)
        for emoji, title_text, desc, badge, mode_key, color in modes:
            card = self._mode_card(emoji, title_text, desc, badge, mode_key, color)
            cards_row.addWidget(card)
        cards_row.addStretch()
        layout.addLayout(cards_row)

        # Stats teaser
        layout.addSpacerItem(QSpacerItem(0, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        info = QLabel(
            f"💡 <b>XP Rewards:</b>  {15} XP per correct  ·  "
            f"+{40} bonus at 80%+  ·  +{40} perfect score bonus"
        )
        info.setFont(QFont("Segoe UI", 11))
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        layout.addStretch()
        scroll.setWidget(content)
        self._set_screen(scroll)

    def _mode_card(self, emoji, title, desc, badge, mode_key, color):
        """Build a single mode selection card."""
        frame = QFrame()
        frame.setFixedSize(260, 230)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame:hover {{
                border: 1px solid {color};
            }}
        """)

        col = QVBoxLayout(frame)
        col.setAlignment(Qt.AlignCenter)
        col.setSpacing(6)
        col.setContentsMargins(20, 18, 20, 18)

        icon = QLabel(emoji)
        icon.setFont(QFont("Segoe UI Emoji", 32))
        icon.setAlignment(Qt.AlignCenter)
        col.addWidget(icon)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 16, QFont.Bold))
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("color: #FFFFFF;")
        col.addWidget(t)

        d = QLabel(desc)
        d.setFont(QFont("Segoe UI", 11))
        d.setAlignment(Qt.AlignCenter)
        d.setWordWrap(True)
        d.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(d)

        # Badge pill
        pill = QLabel(badge)
        pill.setFont(QFont("Segoe UI", 10, QFont.Bold))
        pill.setAlignment(Qt.AlignCenter)
        pill.setFixedHeight(24)
        pill.setStyleSheet(f"""
            background-color: {color}33;
            color: {color};
            border-radius: 12px;
            padding: 2px 12px;
        """)
        col.addWidget(pill, alignment=Qt.AlignCenter)

        col.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        btn = self._styled_btn("Start Quiz", color, width=140, height=38, font_size=12)
        btn.clicked.connect(lambda: self._on_mode_selected(mode_key))
        col.addWidget(btn, alignment=Qt.AlignCenter)

        return frame

    def _on_mode_selected(self, mode):
        """User picked a mode — start loading questions."""
        self._mode = mode
        self._current_idx = 0
        self._score = 0
        self._elapsed_secs = 0

        # Show loading state
        loading = QWidget()
        layout = QVBoxLayout(loading)
        layout.setAlignment(Qt.AlignCenter)
        spinner = QLabel("⏳ Loading questions...")
        spinner.setFont(QFont("Segoe UI", 18))
        spinner.setAlignment(Qt.AlignCenter)
        spinner.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(spinner)
        self._set_screen(loading)

        # Fetch questions in background thread
        self._load_worker = _QuizLoadWorker(mode, self._session_answered_slugs)
        self._load_worker.finished.connect(self._on_questions_loaded)
        self._load_worker.start()

    def _on_questions_loaded(self, questions):
        """Questions received from DB — start the quiz."""
        if not questions:
            self._show_error("No questions available for this mode. Try another!")
            return

        self._questions = questions
        self._timer.start()
        self._show_question()

    def _show_error(self, message):
        """Show an error message with a back button."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("⚠️")
        icon.setFont(QFont("Segoe UI Emoji", 40))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        msg = QLabel(message)
        msg.setFont(QFont("Segoe UI", 16))
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(msg)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        back = self._styled_btn("← Back to Menu", COLORS["primary"])
        back.clicked.connect(self._show_mode_selection)
        layout.addWidget(back, alignment=Qt.AlignCenter)

        self._set_screen(page)

    # ══════════════════════════════════════════════════════════
    # SCREEN 2 — Question (with inline feedback)
    # ══════════════════════════════════════════════════════════

    def _show_question(self):
        """Render the current question screen."""
        q = self._questions[self._current_idx]
        total = len(self._questions)

        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 25, 40, 25)
        page_layout.setSpacing(0)

        # ── Top bar: progress + timer ──
        top = QHBoxLayout()

        progress_text = QLabel(f"Question {self._current_idx + 1} of {total}")
        progress_text.setFont(QFont("Segoe UI", 12, QFont.Bold))
        progress_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        top.addWidget(progress_text)

        top.addStretch()

        # Score pill
        score_pill = QLabel(f"✅ {self._score}")
        score_pill.setFont(QFont("Segoe UI", 12, QFont.Bold))
        score_pill.setStyleSheet(f"""
            color: {COLORS['primary']};
            background-color: {COLORS['primary']}22;
            border-radius: 10px;
            padding: 3px 12px;
        """)
        top.addWidget(score_pill)

        top.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

        # Timer
        self._timer_label = QLabel(f"⏱ {self._elapsed_secs // 60:02d}:{self._elapsed_secs % 60:02d}")
        self._timer_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._timer_label.setStyleSheet(f"color: {COLORS['tertiary']};")
        top.addWidget(self._timer_label)

        page_layout.addLayout(top)
        page_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Progress bar ──
        pbar = QProgressBar()
        pbar.setRange(0, total)
        pbar.setValue(self._current_idx + 1)
        pbar.setFixedHeight(6)
        pbar.setTextVisible(False)
        pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['xp_bar_bg']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 3px;
            }}
        """)
        page_layout.addWidget(pbar)

        page_layout.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Topic tag pill ──
        topic_pill = QLabel(f"📋 {q['topic_tag']}")
        topic_pill.setFont(QFont("Segoe UI", 10))
        topic_pill.setStyleSheet(f"""
            color: {COLORS['secondary']};
            background-color: {COLORS['secondary']}22;
            border-radius: 10px;
            padding: 3px 12px;
        """)
        topic_pill.setFixedHeight(24)
        page_layout.addWidget(topic_pill, alignment=Qt.AlignLeft)

        page_layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Question text ──
        question_label = QLabel(q["question_text"])
        question_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        question_label.setWordWrap(True)
        question_label.setStyleSheet("color: #FFFFFF; line-height: 1.4;")
        page_layout.addWidget(question_label)

        page_layout.addSpacerItem(QSpacerItem(0, 22, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Option buttons (stored for in-place highlighting) ──
        self._option_buttons = []
        option_letters = ["A", "B", "C", "D"]
        for i, option in enumerate(q["options"]):
            opt_btn = QPushButton(f"  {option_letters[i]}.  {option}")
            opt_btn.setFixedHeight(52)
            opt_btn.setFont(QFont("Segoe UI", 13))
            opt_btn.setCursor(Qt.PointingHandCursor)
            opt_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['card_bg']};
                    color: #FFFFFF;
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                    text-align: left;
                    padding-left: 18px;
                }}
                QPushButton:hover {{
                    border: 1px solid {COLORS['primary']};
                    background-color: {COLORS['primary']}15;
                }}
            """)
            opt_btn.clicked.connect(lambda _, idx=i: self._on_answer_selected(idx))
            page_layout.addWidget(opt_btn)
            page_layout.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))
            self._option_buttons.append(opt_btn)

        # ── Inline feedback area (hidden until answer selected) ──
        # Result label (✅ Correct! or ❌ Incorrect)
        self._result_label = QLabel("")
        self._result_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._result_label.setAlignment(Qt.AlignLeft)
        self._result_label.setVisible(False)
        page_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        page_layout.addWidget(self._result_label)

        # Explanation button + card (hidden)
        self._explanation_btn = QPushButton("💡 Show Explanation")
        self._explanation_btn.setFixedHeight(40)
        self._explanation_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._explanation_btn.setCursor(Qt.PointingHandCursor)
        self._explanation_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['card_bg']};
                color: {COLORS['tertiary']};
                border: 1px solid {COLORS['tertiary']}44;
                border-radius: 10px;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['tertiary']}15;
                border: 1px solid {COLORS['tertiary']};
            }}
        """)
        self._explanation_btn.setVisible(False)
        page_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
        page_layout.addWidget(self._explanation_btn)

        # Explanation content (toggleable)
        self._explanation_frame = QFrame()
        self._explanation_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        exp_inner = QVBoxLayout(self._explanation_frame)
        exp_inner.setContentsMargins(16, 12, 16, 12)
        self._explanation_text = QLabel("")
        self._explanation_text.setFont(QFont("Segoe UI", 12))
        self._explanation_text.setWordWrap(True)
        self._explanation_text.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
        exp_inner.addWidget(self._explanation_text)
        self._explanation_frame.setVisible(False)
        page_layout.addWidget(self._explanation_frame)

        # Next Question button (hidden until answer)
        page_layout.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))
        is_last = self._current_idx >= len(self._questions) - 1
        btn_text = "View Results 🏆" if is_last else "Next Question →"
        self._next_btn = self._styled_btn(btn_text, COLORS["primary"], width=220)
        self._next_btn.clicked.connect(self._on_next)
        self._next_btn.setVisible(False)
        page_layout.addWidget(self._next_btn, alignment=Qt.AlignCenter)

        page_layout.addStretch()
        self._set_screen(page)

    # ── Inline Answer Handling ──

    def _on_answer_selected(self, selected_index):
        """Validate answer and show inline feedback on the same screen."""
        from services import QuizService

        q = self._questions[self._current_idx]
        result = QuizService.validate_answer(q, selected_index)
        correct_idx = result["correct_index"]
        is_correct = result["is_correct"]

        if is_correct:
            self._score += 1

        # Track slug
        self._session_answered_slugs.append(q["question_slug"])

        # ── Highlight option buttons ──
        for i, btn in enumerate(self._option_buttons):
            btn.setEnabled(False)
            btn.setCursor(Qt.ArrowCursor)

            if i == correct_idx:
                # Always highlight correct answer green
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['primary']}22;
                        color: #FFFFFF;
                        border: 2px solid {COLORS['primary']};
                        border-radius: 12px;
                        text-align: left;
                        padding-left: 18px;
                    }}
                """)
            elif i == selected_index and not is_correct:
                # Highlight wrong selection in red
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']}22;
                        color: #FFFFFF;
                        border: 2px solid {COLORS['danger']};
                        border-radius: 12px;
                        text-align: left;
                        padding-left: 18px;
                    }}
                """)
            else:
                # Dim other options
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['card_bg']};
                        color: {COLORS['text_secondary']};
                        border: 1px solid {COLORS['border']};
                        border-radius: 12px;
                        text-align: left;
                        padding-left: 18px;
                        opacity: 0.5;
                    }}
                """)

        # ── Show result label ──
        if is_correct:
            self._result_label.setText("✅ Correct!")
            self._result_label.setStyleSheet(f"color: {COLORS['primary']};")
        else:
            self._result_label.setText(f"❌ Incorrect — answer was: {result['correct_answer']}")
            self._result_label.setStyleSheet(f"color: {COLORS['danger']};")
        self._result_label.setVisible(True)

        # ── Show explanation button if explanation exists ──
        explanation = result.get("explanation", "")
        if explanation:
            self._explanation_text.setText(explanation)
            self._explanation_btn.setVisible(True)
            self._explanation_btn.clicked.connect(self._toggle_explanation)
        else:
            self._explanation_btn.setVisible(False)

        # ── Show Next Question button ──
        self._next_btn.setVisible(True)

    def _toggle_explanation(self):
        """Toggle the explanation card visibility."""
        visible = self._explanation_frame.isVisible()
        self._explanation_frame.setVisible(not visible)
        if visible:
            self._explanation_btn.setText("💡 Show Explanation")
        else:
            self._explanation_btn.setText("💡 Hide Explanation")


    def _on_next(self):
        """Advance to next question or results."""
        self._current_idx += 1
        if self._current_idx < len(self._questions):
            self._show_question()
        else:
            self._timer.stop()
            self._submit_results()

    # ══════════════════════════════════════════════════════════
    # SCREEN 4 — Results Summary
    # ══════════════════════════════════════════════════════════

    def _submit_results(self):
        """Submit session to DB in background."""
        # Show loading
        loading = QWidget()
        layout = QVBoxLayout(loading)
        layout.setAlignment(Qt.AlignCenter)
        spinner = QLabel("⏳ Calculating results...")
        spinner.setFont(QFont("Segoe UI", 18))
        spinner.setAlignment(Qt.AlignCenter)
        spinner.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(spinner)
        self._set_screen(loading)

        self._submit_worker = _QuizSubmitWorker(
            self.user_id, self._score, len(self._questions),
            self._mode, self._elapsed_secs,
        )
        self._submit_worker.finished.connect(self._show_results)
        self._submit_worker.start()

    def _show_results(self, result):
        """Display the final results screen."""
        total = result["total"]
        correct = result["correct"]
        pct = result["percentage"]
        total_xp = result.get("total_xp", 0)
        time_secs = result.get("time_secs", self._elapsed_secs)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        # Trophy
        trophy_emoji = "🏆" if pct >= 80 else ("⭐" if pct >= 50 else "📊")
        trophy = QLabel(trophy_emoji)
        trophy.setFont(QFont("Segoe UI Emoji", 50))
        trophy.setAlignment(Qt.AlignCenter)
        layout.addWidget(trophy)

        # Title
        title_text = "Perfect Score!" if pct == 100 else ("Great Job!" if pct >= 80 else ("Quiz Complete!" if pct >= 50 else "Keep Practicing!"))
        result_title = QLabel(title_text)
        result_title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        result_title.setAlignment(Qt.AlignCenter)
        result_title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(result_title)

        layout.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Score
        score_color = COLORS["primary"] if pct >= 70 else (COLORS["tertiary"] if pct >= 40 else COLORS["danger"])
        score_label = QLabel(f"{correct}/{total} ({pct}%)")
        score_label.setFont(QFont("Segoe UI", 34, QFont.Bold))
        score_label.setAlignment(Qt.AlignCenter)
        score_label.setStyleSheet(f"color: {score_color};")
        layout.addWidget(score_label)

        layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Stats card
        stats_frame = QFrame()
        stats_frame.setMaximumWidth(420)
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(24, 18, 24, 18)
        stats_layout.setSpacing(10)

        # XP row
        xp_row = self._stat_row(
            "⚡", "XP Earned",
            f"{total_xp} XP", COLORS["xp_gold"],
        )
        stats_layout.addLayout(xp_row)

        # Base XP
        base_row = self._stat_row(
            "📊", "Base XP",
            f"{result.get('base_xp', 0)} ({correct} × 15)", COLORS["text_secondary"],
        )
        stats_layout.addLayout(base_row)

        # Bonus
        if result.get("bonus_xp", 0) > 0:
            bonus_row = self._stat_row(
                "🎯", "80%+ Bonus", f"+{result['bonus_xp']}", COLORS["primary"],
            )
            stats_layout.addLayout(bonus_row)

        if result.get("perfect_bonus", 0) > 0:
            perfect_row = self._stat_row(
                "💎", "Perfect Bonus", f"+{result['perfect_bonus']}", COLORS["level_purple"],
            )
            stats_layout.addLayout(perfect_row)

        if result.get("multiplier", 1.0) > 1.0:
            multi_row = self._stat_row(
                "🔥", "Challenge Multiplier", f"×{result['multiplier']}", COLORS["tertiary"],
            )
            stats_layout.addLayout(multi_row)

        # Time
        mins = time_secs // 60
        secs = time_secs % 60
        time_row = self._stat_row(
            "⏱", "Time Taken", f"{mins}m {secs}s", COLORS["text_secondary"],
        )
        stats_layout.addLayout(time_row)

        # Level up / badges
        if result.get("leveled_up"):
            level_row = self._stat_row(
                "🎉", "Level Up!", f"Level {result.get('level', '?')}",
                COLORS["level_purple"],
            )
            stats_layout.addLayout(level_row)

        if result.get("new_badges"):
            for badge in result["new_badges"]:
                badge_row = self._stat_row(
                    "🏅", "New Badge", badge.get("name", "Badge"),
                    COLORS["badge_impact"],
                )
                stats_layout.addLayout(badge_row)

        layout.addWidget(stats_frame, alignment=Qt.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 25, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Action buttons
        btns_row = QHBoxLayout()
        btns_row.setSpacing(15)

        retry_btn = self._styled_btn("🔄 Try Again", COLORS["primary"], width=180)
        retry_btn.clicked.connect(self._show_mode_selection)
        btns_row.addWidget(retry_btn)

        back_btn = self._styled_btn("🏠 Dashboard", COLORS["secondary"], width=180)
        back_btn.clicked.connect(self._go_home)
        btns_row.addWidget(back_btn)

        layout.addLayout(btns_row)

        layout.addStretch()
        self._set_screen(page)

    def _stat_row(self, emoji, label, value, color):
        """Build a single stat row for the results card."""
        row = QHBoxLayout()
        icon = QLabel(emoji)
        icon.setFont(QFont("Segoe UI Emoji", 14))
        icon.setFixedWidth(24)
        row.addWidget(icon)

        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row.addWidget(lbl)

        row.addStretch()

        val = QLabel(str(value))
        val.setFont(QFont("Segoe UI", 13, QFont.Bold))
        val.setStyleSheet(f"color: {color};")
        row.addWidget(val)

        return row

    def _go_home(self):
        """Navigate back to dashboard home (index 0)."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'content_stack'):
                parent.content_stack.setCurrentIndex(0)
                # Update nav button styles
                if hasattr(parent, 'nav_buttons') and hasattr(parent, '_navigate_to'):
                    parent._navigate_to(0)
                return
            parent = parent.parent()
        # Fallback: just show mode selection
        self._show_mode_selection()
