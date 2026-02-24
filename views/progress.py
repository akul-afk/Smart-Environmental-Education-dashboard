"""
Progress View — XP Dashboard, Badges, Streaks, Charts, and AI Insights.
PySide6 implementation with Matplotlib chart and DataService.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QScrollArea, QGridLayout,
    QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from constants import COLORS
from app_logger import logger

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class _ProgressDataWorker(QThread):
    """Background worker for loading progress data."""
    finished = Signal(dict)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def run(self):
        from services import DataService
        data = DataService.get_progress_data(self.user_id)
        self.finished.emit(data)


class _AIInsightWorker(QThread):
    """Background thread for fetching AI insight."""
    finished = Signal(str)

    def __init__(self, stats, progress, earned_badges):
        super().__init__()
        self.stats = stats
        self.progress = progress
        self.earned_badges = earned_badges

    def run(self):
        from services import DataService
        insight = DataService.get_ai_insight(self.stats, self.progress, self.earned_badges)
        self.finished.emit(insight)


class ProgressWidget(QWidget):
    """Progress & Achievements view."""

    def __init__(self, user_id=1, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self._data_worker = None
        self._ai_worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self._show_loading()
        self._load_data_async()

    def _show_loading(self):
        loading = QLabel("⏳ Loading progress data...")
        loading.setFont(QFont("Segoe UI", 16))
        loading.setAlignment(Qt.AlignCenter)
        loading.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.main_layout.addWidget(loading)

    def _load_data_async(self):
        self._data_worker = _ProgressDataWorker(self.user_id)
        self._data_worker.finished.connect(self._on_data_loaded)
        self._data_worker.start()

    def _on_data_loaded(self, data):
        # Clear loading state
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.main_layout.addWidget(self.scroll)

        self._build_view(data)

    def _build_view(self, data):
        stats = data["stats"]
        progress = data["progress"]
        earned_badges = data["earned_badges"]
        all_badges = data["all_badges"]
        next_badges = data["next_badges"]
        xp_history = data["xp_history"]
        daily_series = data["daily_series"]
        streak_label = data["streak_label"]

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # Title
        title = QLabel("📊 Progress Dashboard")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        sub = QLabel("Track your eco-learning journey")
        sub.setFont(QFont("Segoe UI", 13))
        sub.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(sub)

        if stats is None:
            msg = QLabel("⏳ Connecting to database...")
            msg.setFont(QFont("Segoe UI", 14))
            msg.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(msg)
            self.scroll.setWidget(content)
            return

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── TOP STATS ROW ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        stats_row.addWidget(self._stat_card("⚡", "Total XP", f"{stats['total_xp']:,}",
                                            COLORS["xp_gold"], f"Daily: {stats['daily_xp']}/{stats['daily_cap']} XP"))
        stats_row.addWidget(self._stat_card_with_bar("🎖️", "Level", str(stats["level"]),
                                                     COLORS["level_purple"], stats["progress_pct"],
                                                     f"{stats['xp_in_level']}/{stats['xp_needed']} XP to next"))
        stats_row.addWidget(self._stat_card("🔥", "Streak", f"{stats['streak_days']} 🔥",
                                            COLORS["streak_orange"], streak_label or "Build your streak!"))
        layout.addLayout(stats_row)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── AI INSIGHT ──
        self.ai_text = QLabel("💡 Press refresh to get your personalized AI insight")
        self.ai_text.setFont(QFont("Segoe UI", 12))
        self.ai_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.ai_text.setWordWrap(True)

        ai_frame = QFrame()
        ai_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['level_purple']};
            }}
        """)
        ai_row = QHBoxLayout(ai_frame)
        ai_row.setContentsMargins(18, 18, 18, 18)
        ai_row.setSpacing(12)

        ai_icon = QLabel("✨")
        ai_icon.setFont(QFont("Segoe UI Emoji", 18))
        ai_row.addWidget(ai_icon)

        ai_col = QVBoxLayout()
        ai_header = QLabel("AI Insight")
        ai_header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        ai_header.setStyleSheet(f"color: {COLORS['level_purple']};")
        ai_col.addWidget(ai_header)
        ai_col.addWidget(self.ai_text)
        ai_row.addLayout(ai_col, stretch=1)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("Get AI Insight")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none; font-size: 18px;
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.1); border-radius: 20px; }}
        """)
        self._refresh_btn = refresh_btn
        refresh_btn.clicked.connect(lambda: self._fetch_ai_insight(stats, progress, earned_badges))
        ai_row.addWidget(refresh_btn)

        layout.addWidget(ai_frame)
        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── PROGRESS + NEXT BADGES ROW ──
        mid_row = QHBoxLayout()
        mid_row.setSpacing(20)

        # Progress Dimensions
        progress_widget = QWidget()
        prog_layout = QVBoxLayout(progress_widget)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_header = QLabel("📈 Progress Dimensions")
        prog_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        prog_header.setStyleSheet("color: #FFFFFF;")
        prog_layout.addWidget(prog_header)
        prog_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        if progress:
            prog_layout.addWidget(self._progress_bar_card("Learning Progress", progress["learning_pct"],
                                                          COLORS["primary"], progress["lessons_completed"],
                                                          progress["total_lessons"], "🎓"))
            prog_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
            prog_layout.addWidget(self._progress_bar_card("Sustainability", progress["sustainability_pct"],
                                                          COLORS["secondary"], progress["challenges_completed"],
                                                          progress["total_challenges"], "🌿"))
            prog_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
            prog_layout.addWidget(self._progress_bar_card("Analytics Exploration", progress["analytics_pct"],
                                                          COLORS["tertiary"], progress["quizzes_completed"],
                                                          progress["total_quizzes"], "📝"))
        mid_row.addWidget(progress_widget, stretch=1)

        # Next Badges
        next_widget = QWidget()
        next_layout = QVBoxLayout(next_widget)
        next_layout.setContentsMargins(0, 0, 0, 0)
        next_header = QLabel("🎯 Next Badges")
        next_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        next_header.setStyleSheet("color: #FFFFFF;")
        next_layout.addWidget(next_header)
        next_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        if next_badges:
            for nb in next_badges:
                next_layout.addWidget(self._next_badge_card(nb))
                next_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
        else:
            done = QLabel("All badges earned! 🎉")
            done.setStyleSheet(f"color: {COLORS['text_secondary']};")
            next_layout.addWidget(done)

        next_layout.addStretch()
        mid_row.addWidget(next_widget, stretch=1)

        layout.addLayout(mid_row)
        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── XP CHART (Matplotlib) ──
        chart_header = QLabel("📊 XP Growth (Last 14 Days)")
        chart_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        chart_header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(chart_header)
        layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        chart_widget = self._build_chart(daily_series)
        layout.addWidget(chart_widget)
        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── BADGES GRID ──
        earned_badge_names = {b["name"] for b in earned_badges}
        badges_header = QLabel(f"🏆 Badges ({len(earned_badges)}/{len(all_badges)})")
        badges_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        badges_header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(badges_header)
        layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        badge_grid = QGridLayout()
        badge_grid.setSpacing(10)
        for i, b in enumerate(all_badges):
            is_earned = b["name"] in earned_badge_names
            badge_grid.addWidget(self._badge_chip(b, is_earned), i // 6, i % 6)
        layout.addLayout(badge_grid)
        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── RECENT ACTIVITY ──
        act_header = QLabel("⚡ Recent Activity")
        act_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        act_header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(act_header)
        layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        action_labels = {
            "lesson_complete": "📘 Lesson Completed",
            "quiz_attempt": "📝 Quiz Attempted",
            "quiz_correct": "✅ Correct Answer",
            "quiz_perfect": "🌟 Perfect Score",
            "challenge_complete": "🌿 Challenge Done",
            "simulation_play": "🏙 Simulation Played",
        }

        act_frame = QFrame()
        act_frame.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 12px; }}
        """)
        act_list = QVBoxLayout(act_frame)
        act_list.setContentsMargins(10, 10, 10, 10)
        act_list.setSpacing(2)

        if xp_history:
            for h in xp_history[:8]:
                label = action_labels.get(h["action_type"], h["action_type"])
                ts = str(h["timestamp"])[:16] if h["timestamp"] else ""
                row = QHBoxLayout()
                act_label = QLabel(label)
                act_label.setFont(QFont("Segoe UI", 11))
                act_label.setStyleSheet("color: #FFFFFF;")
                row.addWidget(act_label, stretch=1)

                xp_lbl = QLabel(f"+{h['xp_earned']} XP")
                xp_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
                xp_lbl.setStyleSheet(f"color: {COLORS['xp_gold']};")
                row.addWidget(xp_lbl)

                ts_lbl = QLabel(ts)
                ts_lbl.setFont(QFont("Segoe UI", 9))
                ts_lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
                row.addWidget(ts_lbl)

                wrapper = QWidget()
                wrapper.setLayout(row)
                act_list.addWidget(wrapper)
        else:
            no_act = QLabel("No activity yet. Start learning!")
            no_act.setStyleSheet(f"color: {COLORS['text_secondary']};")
            act_list.addWidget(no_act)

        layout.addWidget(act_frame)
        layout.addStretch()

        self.scroll.setWidget(content)

    # ── Helper Widgets ──
    def _stat_card(self, icon, label, value, color, sub_text):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 15px; }}
        """)
        col = QVBoxLayout(frame)
        col.setContentsMargins(20, 20, 20, 20)
        col.setAlignment(Qt.AlignCenter)

        row = QHBoxLayout()
        row.setSpacing(8)
        i = QLabel(icon)
        i.setFont(QFont("Segoe UI Emoji", 18))
        row.addWidget(i)
        l = QLabel(label)
        l.setFont(QFont("Segoe UI", 12))
        l.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row.addWidget(l)
        col.addLayout(row)

        v = QLabel(value)
        v.setFont(QFont("Segoe UI", 30, QFont.Bold))
        v.setStyleSheet(f"color: {color};")
        v.setAlignment(Qt.AlignCenter)
        col.addWidget(v)

        col.addSpacerItem(QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        s = QLabel(sub_text)
        s.setFont(QFont("Segoe UI", 10))
        s.setStyleSheet(f"color: {COLORS['text_secondary']};")
        s.setAlignment(Qt.AlignCenter)
        col.addWidget(s)

        return frame

    def _stat_card_with_bar(self, icon, label, value, color, pct, sub_text):
        frame = self._stat_card(icon, label, value, color, sub_text)
        col = frame.layout()

        bar = QProgressBar()
        bar.setFixedHeight(8)
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS['xp_bar_bg']}; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}
        """)
        col.insertWidget(col.count() - 1, bar)
        return frame

    def _progress_bar_card(self, label, pct, color, completed, total, icon):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 12px; }}
        """)
        col = QVBoxLayout(frame)
        col.setContentsMargins(15, 15, 15, 15)
        col.setSpacing(6)

        row = QHBoxLayout()
        i = QLabel(icon)
        i.setFont(QFont("Segoe UI Emoji", 14))
        row.addWidget(i)
        l = QLabel(label)
        l.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        l.setStyleSheet("color: #FFFFFF;")
        row.addWidget(l, stretch=1)
        p = QLabel(f"{pct}%")
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.setStyleSheet(f"color: {color};")
        row.addWidget(p)
        col.addLayout(row)

        bar = QProgressBar()
        bar.setFixedHeight(10)
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS['xp_bar_bg']}; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 5px; }}
        """)
        col.addWidget(bar)

        detail = QLabel(f"{completed}/{total} completed")
        detail.setFont(QFont("Segoe UI", 10))
        detail.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(detail)

        return frame

    def _next_badge_card(self, nb):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 10px; }}
        """)
        col = QVBoxLayout(frame)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(4)

        name = QLabel(nb["name"])
        name.setFont(QFont("Segoe UI", 12, QFont.Bold))
        name.setStyleSheet("color: #FFFFFF;")
        col.addWidget(name)

        if "description" in nb and nb["description"]:
            desc = QLabel(nb["description"])
            desc.setFont(QFont("Segoe UI", 10))
            desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
            desc.setWordWrap(True)
            col.addWidget(desc)

        bar = QProgressBar()
        bar.setFixedHeight(6)
        bar.setRange(0, 100)
        bar.setValue(nb["progress_pct"])
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS['xp_bar_bg']}; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {COLORS['primary']}; border-radius: 3px; }}
        """)
        col.addWidget(bar)

        detail = QLabel(f"{nb['current']}/{nb['threshold']} ({nb['progress_pct']}%)")
        detail.setFont(QFont("Segoe UI", 9))
        detail.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(detail)

        return frame

    def _badge_chip(self, badge, is_earned):
        frame = QFrame()
        frame.setFixedSize(100, 100)
        bg = COLORS["card_bg"] if is_earned else COLORS["background"]
        border_color = COLORS["xp_gold"] if is_earned else COLORS["border"]
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: 10px;
                border: 2px solid {border_color};
            }}
        """)

        col = QVBoxLayout(frame)
        col.setAlignment(Qt.AlignCenter)
        col.setSpacing(4)
        col.setContentsMargins(6, 6, 6, 6)

        icon_map = {
            "SCHOOL": "🎓", "QUIZ": "📝", "LIGHTBULB": "💡", "STAR": "⭐",
            "LOCAL_FIRE_DEPARTMENT": "🔥", "EMOJI_EVENTS": "🏆", "MENU_BOOK": "📖",
            "MILITARY_TECH": "🎖️", "PUBLIC": "🌍", "WHATSHOT": "🔥",
            "PSYCHOLOGY": "🧠", "ANALYTICS": "📊",
        }
        icon_emoji = icon_map.get(badge.get("icon", ""), "⭐")
        icon_lbl = QLabel(icon_emoji)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
        icon_lbl.setAlignment(Qt.AlignCenter)
        col.addWidget(icon_lbl)

        name = QLabel(badge["name"])
        name.setFont(QFont("Segoe UI", 9, QFont.Bold if is_earned else QFont.Normal))
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {'#FFFFFF' if is_earned else COLORS['text_secondary']};")
        col.addWidget(name)

        tier = QLabel(badge["tier"])
        tier.setFont(QFont("Segoe UI", 7))
        tier.setAlignment(Qt.AlignCenter)
        tier.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(tier)

        return frame

    def _build_chart(self, daily_series):
        """Build a Matplotlib bar chart for XP growth."""
        fig = Figure(figsize=(7, 1.8), dpi=100)
        fig.patch.set_facecolor(COLORS["card_bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["card_bg"])

        if daily_series:
            dates = [d[0][-5:] if len(d[0]) > 5 else d[0] for d in daily_series]
            values = [d[1] for d in daily_series]
            bars = ax.bar(dates, values, color=COLORS["primary"], width=0.6, zorder=3)
            ax.set_ylim(0, max(values) * 1.2 if values else 10)

            for bar_obj, val in zip(bars, values):
                if val > 0:
                    ax.text(bar_obj.get_x() + bar_obj.get_width() / 2, bar_obj.get_height() + 1,
                            str(val), ha='center', va='bottom', fontsize=7, color=COLORS["text_secondary"])
        else:
            ax.text(0.5, 0.5, "Start earning XP to see your chart!",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=10, color=COLORS["text_secondary"])

        ax.tick_params(colors=COLORS["text_secondary"], labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(COLORS["border"])
        ax.spines['bottom'].set_color(COLORS["border"])
        fig.tight_layout(pad=1.0)

        canvas = FigureCanvas(fig)
        canvas.setFixedHeight(160)
        canvas.setStyleSheet(f"background-color: {COLORS['card_bg']}; border-radius: 12px;")
        return canvas

    def _fetch_ai_insight(self, stats, progress, earned_badges):
        self.ai_text.setText("🤔 Thinking...")
        self.ai_text.setStyleSheet(f"color: {COLORS['tertiary']};")
        if hasattr(self, '_refresh_btn'):
            self._refresh_btn.setEnabled(False)
            self._refresh_btn.setText("⏳")
        self._ai_worker = _AIInsightWorker(stats, progress, earned_badges)
        self._ai_worker.finished.connect(self._on_ai_insight)
        self._ai_worker.start()

    def _on_ai_insight(self, text):
        self.ai_text.setText(text)
        self.ai_text.setStyleSheet(f"color: #FFFFFF;")
        if hasattr(self, '_refresh_btn'):
            self._refresh_btn.setEnabled(True)
            self._refresh_btn.setText("🔄")
