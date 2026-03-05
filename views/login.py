"""
Login / Signup View — Combined authentication screen with tab toggle.
PySide6 implementation with glassmorphism-style card.
Uses DataService for all database operations.
"""

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QSizePolicy, QSpacerItem, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from constants import COLORS
from app_logger import logger


class _AuthWorker(QThread):
    """Background worker for authentication operations."""
    finished = Signal(dict)

    def __init__(self, mode, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        from services import DataService
        if self.mode == "login":
            result = DataService.login(self.kwargs["email"], self.kwargs["password"])
        else:
            result = DataService.register(
                self.kwargs["username"], self.kwargs["email"], self.kwargs["password"]
            )
        self.finished.emit(result)


class LoginWidget(QWidget):
    """Combined Login / Signup view."""

    def __init__(self, on_login_success=None, parent=None):
        super().__init__(parent)
        self.on_login_success = on_login_success
        self.mode = "login"  # "login" or "signup"
        self._auth_worker = None
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        # Glass card container
        self.card = QFrame()
        self.card.setFixedWidth(420)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 20px;
            }}
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 25, 30, 20)
        card_layout.setSpacing(0)

        # Logo
        logo = QLabel("🌿")
        logo.setFont(QFont("Segoe UI Emoji", 32))
        logo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(logo)

        card_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Title
        title = QLabel("Smart Environmental Education")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; border: none;")
        card_layout.addWidget(title)

        tagline = QLabel("Learn, Grow, Protect the Planet")
        tagline.setFont(QFont("Segoe UI", 12))
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        card_layout.addWidget(tagline)

        card_layout.addSpacerItem(QSpacerItem(0, 18, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Tab row
        tab_row = QHBoxLayout()
        tab_row.setAlignment(Qt.AlignCenter)
        tab_row.setSpacing(10)

        self.login_tab_btn = QPushButton("Login")
        self.signup_tab_btn = QPushButton("Sign Up")
        for btn in [self.login_tab_btn, self.signup_tab_btn]:
            btn.setFixedHeight(40)
            btn.setFont(QFont("Segoe UI", 13))
            btn.setCursor(Qt.PointingHandCursor)

        self.login_tab_btn.clicked.connect(lambda: self._switch_mode("login"))
        self.signup_tab_btn.clicked.connect(lambda: self._switch_mode("signup"))

        tab_row.addWidget(self.login_tab_btn)
        tab_row.addWidget(self.signup_tab_btn)
        card_layout.addLayout(tab_row)

        card_layout.addSpacerItem(QSpacerItem(0, 18, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Form stack
        self.form_stack = QStackedWidget()
        self.form_stack.setStyleSheet("background-color: transparent; border: none;")

        # Login form
        login_form = QWidget()
        login_form.setStyleSheet("border: none;")
        login_layout = QVBoxLayout(login_form)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.setSpacing(8)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("📧  Email")
        self.login_email.setFixedHeight(48)
        self.login_email.setMaxLength(255)
        login_layout.addWidget(self.login_email)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("🔒  Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setFixedHeight(48)
        self.login_password.setMaxLength(128)
        login_layout.addWidget(self.login_password)

        self.login_error = QLabel("")
        self.login_error.setFont(QFont("Segoe UI", 11))
        self.login_error.setStyleSheet(f"color: {COLORS['danger']};")
        self.login_error.setAlignment(Qt.AlignCenter)
        self.login_error.setWordWrap(True)
        self.login_error.setVisible(False)
        login_layout.addWidget(self.login_error)

        login_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedHeight(48)
        self.login_btn.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{ background-color: #1aaf4f; }}
            QPushButton:pressed {{ background-color: #178a3f; }}
        """)
        self.login_btn.clicked.connect(self._do_login)
        self.login_email.returnPressed.connect(self._do_login)
        self.login_password.returnPressed.connect(self._do_login)
        login_layout.addWidget(self.login_btn)

        login_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        switch_signup_row = QHBoxLayout()
        switch_signup_row.setAlignment(Qt.AlignCenter)
        switch_signup_row.addWidget(self._plain_label("Don't have an account?"))
        switch_signup_link = QPushButton("Sign Up")
        switch_signup_link.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none;
                color: {COLORS['primary']}; font-weight: bold;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        switch_signup_link.setCursor(Qt.PointingHandCursor)
        switch_signup_link.clicked.connect(lambda: self._switch_mode("signup"))
        switch_signup_row.addWidget(switch_signup_link)
        login_layout.addLayout(switch_signup_row)

        self.form_stack.addWidget(login_form)

        # Signup form
        signup_form = QWidget()
        signup_form.setStyleSheet("border: none;")
        signup_layout = QVBoxLayout(signup_form)
        signup_layout.setContentsMargins(0, 0, 0, 0)
        signup_layout.setSpacing(8)

        self.signup_username = QLineEdit()
        self.signup_username.setPlaceholderText("👤  Username (letters, numbers, underscores)")
        self.signup_username.setFixedHeight(48)
        self.signup_username.setMaxLength(30)
        signup_layout.addWidget(self.signup_username)

        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("📧  Email")
        self.signup_email.setFixedHeight(48)
        self.signup_email.setMaxLength(255)
        signup_layout.addWidget(self.signup_email)

        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("🔒  Password (8+ chars, uppercase, digit)")
        self.signup_password.setEchoMode(QLineEdit.Password)
        self.signup_password.setFixedHeight(48)
        self.signup_password.setMaxLength(128)
        signup_layout.addWidget(self.signup_password)

        self.signup_confirm = QLineEdit()
        self.signup_confirm.setPlaceholderText("🔒  Confirm Password")
        self.signup_confirm.setEchoMode(QLineEdit.Password)
        self.signup_confirm.setFixedHeight(48)
        self.signup_confirm.setMaxLength(128)
        signup_layout.addWidget(self.signup_confirm)

        self.signup_error = QLabel("")
        self.signup_error.setFont(QFont("Segoe UI", 11))
        self.signup_error.setStyleSheet(f"color: {COLORS['danger']};")
        self.signup_error.setAlignment(Qt.AlignCenter)
        self.signup_error.setWordWrap(True)
        self.signup_error.setVisible(False)
        signup_layout.addWidget(self.signup_error)

        signup_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setFixedHeight(48)
        self.signup_btn.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.signup_btn.setCursor(Qt.PointingHandCursor)
        self.signup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{ background-color: #1aaf4f; }}
            QPushButton:pressed {{ background-color: #178a3f; }}
        """)
        self.signup_btn.clicked.connect(self._do_signup)
        signup_layout.addWidget(self.signup_btn)

        signup_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        switch_login_row = QHBoxLayout()
        switch_login_row.setAlignment(Qt.AlignCenter)
        switch_login_row.addWidget(self._plain_label("Already have an account?"))
        switch_login_link = QPushButton("Login")
        switch_login_link.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none;
                color: {COLORS['primary']}; font-weight: bold;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        switch_login_link.setCursor(Qt.PointingHandCursor)
        switch_login_link.clicked.connect(lambda: self._switch_mode("login"))
        switch_login_row.addWidget(switch_login_link)
        signup_layout.addLayout(switch_login_row)

        self.form_stack.addWidget(signup_form)

        card_layout.addWidget(self.form_stack)

        outer.addWidget(self.card)

        # Initial tab styling
        self._update_tab_styles()

    def _plain_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        return lbl

    def _switch_mode(self, mode):
        self.mode = mode
        self.login_error.setVisible(False)
        self.signup_error.setVisible(False)
        self.form_stack.setCurrentIndex(0 if mode == "login" else 1)
        self._update_tab_styles()

    def _update_tab_styles(self):
        is_login = self.mode == "login"
        active_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: none;
                border-bottom: 3px solid {COLORS['primary']};
                border-radius: 0px;
                font-weight: bold;
                padding: 8px 30px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-bottom: 3px solid transparent;
                border-radius: 0px;
                padding: 8px 30px;
            }}
            QPushButton:hover {{ color: #FFFFFF; }}
        """
        self.login_tab_btn.setStyleSheet(active_style if is_login else inactive_style)
        self.signup_tab_btn.setStyleSheet(inactive_style if is_login else active_style)

    def _validate_email(self, email):
        return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

    def _show_error(self, label, msg):
        label.setText(msg)
        label.setVisible(True)

    def _set_buttons_enabled(self, enabled):
        """Enable/disable auth buttons to prevent double-submit."""
        self.login_btn.setEnabled(enabled)
        self.signup_btn.setEnabled(enabled)

    def _do_login(self):
        self.login_error.setVisible(False)
        email = self.login_email.text().strip()
        password = self.login_password.text()

        if not email:
            return self._show_error(self.login_error, "Please enter your email")
        if not password:
            return self._show_error(self.login_error, "Please enter your password")
        if not self._validate_email(email):
            return self._show_error(self.login_error, "Please enter a valid email address")

        self._set_buttons_enabled(False)
        self._auth_worker = _AuthWorker("login", email=email, password=password)
        self._auth_worker.finished.connect(self._on_login_result)
        self._auth_worker.start()

    def _on_login_result(self, result):
        self._set_buttons_enabled(True)
        if result["success"]:
            if self.on_login_success:
                self.on_login_success(result["user_id"], result["username"])
        else:
            self._show_error(self.login_error, result["error"])

    def _do_signup(self):
        self.signup_error.setVisible(False)
        username = self.signup_username.text().strip()
        email = self.signup_email.text().strip()
        password = self.signup_password.text()
        confirm = self.signup_confirm.text()

        if not username:
            return self._show_error(self.signup_error, "Please enter a username")
        if not email:
            return self._show_error(self.signup_error, "Please enter your email")
        if not self._validate_email(email):
            return self._show_error(self.signup_error, "Please enter a valid email address")
        if not password:
            return self._show_error(self.signup_error, "Please enter a password")
        if password != confirm:
            return self._show_error(self.signup_error, "Passwords don't match")

        # Password strength and username validation happen server-side in auth.py

        self._set_buttons_enabled(False)
        self._auth_worker = _AuthWorker("signup", username=username, email=email, password=password)
        self._auth_worker.finished.connect(self._on_signup_result)
        self._auth_worker.start()

    def _on_signup_result(self, result):
        self._set_buttons_enabled(True)
        if result["success"]:
            if self.on_login_success:
                self.on_login_success(result["user_id"], result["username"])
        else:
            self._show_error(self.signup_error, result["error"])
