"""
Home View – XP status, progress bars, next badges, and feature cards.
PySide6 implementation using DataService for data loading.
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


class _HomeDataWorker(QThread):
    """Background worker for loading home view data."""
    finished = Signal(dict)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def run(self):
        from services import DataService
        data = DataService.get_home_data(self.user_id)
        self.finished.emit(data)


class HomeWidget(QWidget):
    """Home dashboard view showing XP, level, streak, badges, and feature cards."""

    def __init__(self, user_id=1, on_navigate=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.on_navigate = on_navigate
        self._worker = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Show loading state first, then load data in background
        self._show_loading()
        self._load_data_async()

    def _show_loading(self):
        loading = QLabel("⏳ Loading dashboard...")
        loading.setFont(QFont("Segoe UI", 16))
        loading.setAlignment(Qt.AlignCenter)
        loading.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.main_layout.addWidget(loading)

    def _load_data_async(self):
        self._worker = _HomeDataWorker(self.user_id)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.start()

    def _on_data_loaded(self, data):
        # Clear loading state
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._build_ui(data["stats"], data["next_badges"], data["streak_label"], data["progress"])

    def _build_ui(self, stats, next_badges, streak_label, progress):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # Title Section
        header = QHBoxLayout()
        title = QLabel(f"🌿 Welcome back, {stats['username'] if stats else 'Learner'}!")
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        # Streak badge
        streak_days = stats["streak_days"] if stats else 0
        fire_emoji = "🔥" if streak_days >= 3 else "📅"
        streak_badge = QLabel(f"{fire_emoji} {streak_days} day streak")
        streak_badge.setFont(QFont("Segoe UI", 13, QFont.Bold))
        streak_badge.setStyleSheet(f"""
            color: {COLORS['streak_orange']};
            background-color: {COLORS['card_bg']};
            border: 1px solid {COLORS['streak_orange']};
            border-radius: 15px;
            padding: 5px 15px;
        """)
        header.addWidget(streak_badge)
        layout.addLayout(header)

        layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # XP Status Bar
        if stats:
            xp_frame = QFrame()
            xp_frame.setStyleSheet(f"""
                QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 15px; }}
            """)
            xp_layout = QVBoxLayout(xp_frame)
            xp_layout.setContentsMargins(20, 20, 20, 20)

            xp_header = QHBoxLayout()
            lvl = QLabel(f"⚡ Level {stats['level']}")
            lvl.setFont(QFont("Segoe UI", 16, QFont.Bold))
            lvl.setStyleSheet(f"color: {COLORS['level_purple']};")
            xp_header.addWidget(lvl)
            xp_header.addStretch()
            xp_val = QLabel(f"{stats['total_xp']:,} XP")
            xp_val.setFont(QFont("Segoe UI", 16, QFont.Bold))
            xp_val.setStyleSheet(f"color: {COLORS['xp_gold']};")
            xp_header.addWidget(xp_val)
            xp_layout.addLayout(xp_header)

            bar = QProgressBar()
            bar.setFixedHeight(10)
            bar.setRange(0, 100)
            bar.setValue(stats["progress_pct"])
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: {COLORS['xp_bar_bg']}; border-radius: 5px; }}
                QProgressBar::chunk {{ background-color: {COLORS['xp_gold']}; border-radius: 5px; }}
            """)
            xp_layout.addWidget(bar)

            xp_detail = QLabel(f"{stats['xp_in_level']}/{stats['xp_needed']} XP to Level {stats['level'] + 1}")
            xp_detail.setFont(QFont("Segoe UI", 10))
            xp_detail.setStyleSheet(f"color: {COLORS['text_secondary']};")
            xp_layout.addWidget(xp_detail)

            layout.addWidget(xp_frame)

        layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Progress Bars Row
        if progress:
            progress_row = QHBoxLayout()
            progress_row.setSpacing(15)
            progress_row.addWidget(self._progress_card("🎓", "Learning", progress["learning_pct"],
                                                       COLORS["primary"], f"{progress['lessons_completed']}/{progress['total_lessons']} lessons"))
            progress_row.addWidget(self._progress_card("📝", "Quizzes", progress["analytics_pct"],
                                                       COLORS["tertiary"], f"{progress['quizzes_completed']}/{progress['total_quizzes']} quizzes"))
            progress_row.addWidget(self._progress_card("🌿", "Sustainability", progress["sustainability_pct"],
                                                       COLORS["secondary"], f"{progress['challenges_completed']}/{progress['total_challenges']} challenges"))
            layout.addLayout(progress_row)

        layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Next Badges Section
        if next_badges:
            badge_header = QLabel("🎯 Next Badges")
            badge_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
            badge_header.setStyleSheet("color: #FFFFFF;")
            layout.addWidget(badge_header)

            layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

            badge_row = QHBoxLayout()
            badge_row.setSpacing(12)
            for nb in next_badges:
                badge_row.addWidget(self._badge_preview(nb))
            badge_row.addStretch()
            layout.addLayout(badge_row)

        layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Feature Cards
        cards_header = QLabel("🚀 Quick Actions")
        cards_header.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        cards_header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(cards_header)

        layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        cards = [
            ("📚", "Learn", "Explore concepts", COLORS["primary"], 2),
            ("🔬", "Quiz Mode", "Test your knowledge", COLORS["secondary"], 1),
            ("🏆", "Progress", "View your stats", COLORS["tertiary"], 3),
        ]
        for emoji, title, desc, color, nav_idx in cards:
            cards_row.addWidget(self._feature_card(emoji, title, desc, color, nav_idx))
        layout.addLayout(cards_row)

        layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

    def _progress_card(self, icon, label, pct, color, detail):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 12px; }}")
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
        bar.setFixedHeight(8)
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS['xp_bar_bg']}; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}
        """)
        col.addWidget(bar)

        d = QLabel(detail)
        d.setFont(QFont("Segoe UI", 10))
        d.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(d)

        return frame

    def _badge_preview(self, nb):
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

    def _feature_card(self, emoji, title, desc, color, nav_idx):
        frame = QFrame()
        frame.setFixedHeight(120)
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['card_bg']}; border-radius: 12px; }}
        """)
        col = QVBoxLayout(frame)
        col.setContentsMargins(15, 15, 15, 15)
        col.setSpacing(4)

        icon = QLabel(emoji)
        icon.setFont(QFont("Segoe UI Emoji", 22))
        col.addWidget(icon)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet("color: #FFFFFF;")
        col.addWidget(t)

        d = QLabel(desc)
        d.setFont(QFont("Segoe UI", 10))
        d.setStyleSheet(f"color: {COLORS['text_secondary']};")
        col.addWidget(d)

        btn = QPushButton("Go →")
        btn.setFixedSize(60, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #FFFFFF;
                border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(lambda: self.on_navigate(nav_idx) if self.on_navigate else None)
        col.addWidget(btn)

        return frame
