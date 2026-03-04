"""
Smart Environmental Education Desktop App
A modern desktop application for environmental education with XP & progress tracking.
Built with PySide6 (Qt for Python).
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont

from constants import COLORS, WINDOW, GLOBAL_STYLESHEET
from app_logger import logger
from views import LandingWidget, LoginWidget, HomeWidget, DataExplorerWidget, LearnWidget, ProgressWidget, QuizCenterWidget, CarbonCycleView


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Environmental Education")
        self.setMinimumSize(WINDOW["min_width"], WINDOW["min_height"])
        self.resize(1100, 700)

        # Session state
        self.user_id = None
        self.username = None

        # Initialize database
        try:
            from database import init_db
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Database init error: %s", e)

        # Main stacked widget: Landing / Login / Dashboard
        self.main_stack = QStackedWidget()
        self.setCentralWidget(self.main_stack)

        # Create screens
        self._build_landing()
        self._build_login()

        # Start on landing
        self.main_stack.setCurrentIndex(0)

    # ── Landing Screen ──
    def _build_landing(self):
        self.landing_widget = LandingWidget(on_enter=self._show_login)
        self.main_stack.addWidget(self.landing_widget)

    # ── Login Screen ──
    def _build_login(self):
        self.login_widget = LoginWidget(on_login_success=self._on_login_success)
        self.main_stack.addWidget(self.login_widget)

    # ── Dashboard ──
    def _build_dashboard(self):
        """Build the main dashboard with sidebar nav + content area."""
        dashboard = QWidget()
        layout = QHBoxLayout(dashboard)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setFixedWidth(110)
        sidebar.setStyleSheet(f"background-color: {COLORS['card_bg']};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 15)
        sidebar_layout.setSpacing(5)

        # Nav buttons
        nav_items = [
            ("🏠", "Home"),
            ("📊", "Explorer"),
            ("📚", "Learn"),
            ("🏆", "Progress"),
            ("🧠", "Quiz"),
            ("🌍", "Phenomenas"),
        ]

        self.nav_buttons = []
        for emoji, label in nav_items:
            btn = QPushButton(f"{emoji}\n{label}")
            btn.setFixedSize(100, 70)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setStyleSheet(self._nav_btn_style(False))
            btn.setCursor(Qt.PointingHandCursor)
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn, alignment=Qt.AlignHCenter)

        # Connect nav buttons
        for i, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(lambda checked, idx=i: self._navigate_to(idx))

        # Spacer
        sidebar_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # User info at bottom of sidebar
        user_icon = QLabel("👤")
        user_icon.setFont(QFont("Segoe UI", 22))
        user_icon.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(user_icon)

        user_label = QLabel(self.username or "User")
        user_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        user_label.setAlignment(Qt.AlignCenter)
        user_label.setStyleSheet("color: #FFFFFF;")
        sidebar_layout.addWidget(user_label)

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedWidth(80)
        logout_btn.setFont(QFont("Segoe UI", 9))
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                padding: 5px;
            }}
            QPushButton:hover {{
                color: {COLORS['danger']};
            }}
        """)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self._do_logout)
        sidebar_layout.addWidget(logout_btn, alignment=Qt.AlignHCenter)

        layout.addWidget(sidebar)

        # ── Content Area ──
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background-color: {COLORS['background']};")

        # Create content widgets
        self.home_widget = HomeWidget(user_id=self.user_id, on_navigate=self._navigate_to)
        self.explorer_widget = DataExplorerWidget(user_id=self.user_id)
        self.learn_widget = LearnWidget(user_id=self.user_id)
        self.progress_widget = ProgressWidget(user_id=self.user_id)
        self.quiz_center_widget = QuizCenterWidget(user_id=self.user_id)
        self.carbon_cycle_widget = CarbonCycleView()

        self.content_stack.addWidget(self.home_widget)
        self.content_stack.addWidget(self.explorer_widget)
        self.content_stack.addWidget(self.learn_widget)
        self.content_stack.addWidget(self.progress_widget)
        self.content_stack.addWidget(self.quiz_center_widget)
        self.content_stack.addWidget(self.carbon_cycle_widget)

        layout.addWidget(self.content_stack)

        # Select Home by default
        self._navigate_to(0)

        return dashboard

    def _nav_btn_style(self, selected: bool) -> str:
        if selected:
            return f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['primary']};
                    border: none;
                    border-left: 3px solid {COLORS['primary']};
                    border-radius: 0px;
                    font-weight: bold;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    color: #FFFFFF;
                    background-color: rgba(255, 255, 255, 0.05);
                }}
            """

    def _navigate_to(self, index: int):
        """Switch content area to the given tab index."""
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setStyleSheet(self._nav_btn_style(i == index))

    # ── Navigation Callbacks ──
    def _show_login(self):
        self.main_stack.setCurrentIndex(1)

    def _on_login_success(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        logger.info("Logged in as %s (ID: %d)", username, user_id)

        # Update streak
        from services import DataService
        DataService.update_streak(user_id)

        # Build and show dashboard
        dashboard = self._build_dashboard()
        self.main_stack.addWidget(dashboard)
        self.main_stack.setCurrentWidget(dashboard)

    def _do_logout(self):
        logger.info("User logged out: %s", self.username)
        self.user_id = None
        self.username = None

        # Remove dashboard widget(s) beyond index 1
        while self.main_stack.count() > 2:
            w = self.main_stack.widget(2)
            self.main_stack.removeWidget(w)
            w.deleteLater()

        # Show landing
        self.main_stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
