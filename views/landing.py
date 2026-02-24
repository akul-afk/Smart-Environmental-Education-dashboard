"""
Landing Screen View for Smart Environmental Education App.
PySide6 implementation with styled Get Started button.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from constants import COLORS


class LandingWidget(QWidget):
    """Landing screen with animated Get Started button."""

    def __init__(self, on_enter=None, parent=None):
        super().__init__(parent)
        self.on_enter = on_enter
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Spacer top
        layout.addSpacerItem(QSpacerItem(0, 80, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Globe icon
        icon_label = QLabel("🌍")
        icon_label.setFont(QFont("Segoe UI Emoji", 72))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        layout.addSpacerItem(QSpacerItem(0, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Title
        title = QLabel("Smart Environmental Education")
        title.setFont(QFont("Segoe UI", 38, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['primary']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Subtitle
        subtitle = QLabel("Explore, Learn, and Protect Our Planet")
        subtitle.setFont(QFont("Segoe UI", 18, QFont.Light))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacerItem(QSpacerItem(0, 50, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Get Started button
        self.enter_btn = QPushButton("Get Started")
        self.enter_btn.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.enter_btn.setFixedSize(280, 65)
        self.enter_btn.setCursor(Qt.PointingHandCursor)
        self.enter_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
                border: none;
                border-radius: 32px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1aaf4f;
            }}
            QPushButton:pressed {{
                background-color: #178a3f;
            }}
        """)
        self.enter_btn.clicked.connect(self._on_enter_click)
        layout.addWidget(self.enter_btn, alignment=Qt.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Version
        version = QLabel("v2.0")
        version.setFont(QFont("Segoe UI", 11))
        version.setStyleSheet(f"color: {COLORS['text_secondary']};")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # Spacer bottom
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _on_enter_click(self):
        if self.on_enter:
            self.on_enter()
