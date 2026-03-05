"""
Phenomena View — QTabWidget-based hub for interactive climate animations.

Each tab loads a local HTML animation inside a QWebEngineView.
To add a new phenomenon, append to the PHENOMENA list below.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings

from constants import COLORS

_ANIM_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "animations"
)

# ── Registry: (tab_label, html_file, short_description) ──
PHENOMENA = [
    (
        "🔄  Carbon Cycle",
        "carbon_cycle.html",
        "Explore how carbon moves between the atmosphere, forests, oceans, soil, and fossil fuels.",
    ),
    (
        "☀️  Greenhouse Effect",
        "greenhouse.html",
        "Visualize how solar radiation and greenhouse gases trap heat in Earth's atmosphere.",
    ),
    (
        "🌊  Ocean Acidification",
        "ocean_acidification.html",
        "See how dissolved CO₂ lowers ocean pH, bleaching coral reefs and disrupting marine life.",
    ),
    (
        "⚡  Renewable Energy",
        "renewable_energy.html",
        "Discover how solar, wind, and hydro systems generate clean electricity for the future.",
    ),
    (
        "🌌  Aurora Borealis",
        "aurora_borealis.html",
        "Watch the stunning Northern Lights form as solar particles collide with our atmosphere.",
    ),
]


class _AnimationPage(QWidget):
    """Single tab page: description label + full-screen QWebEngineView."""

    def __init__(self, html_file: str, description: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        desc = QLabel(description)
        desc.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        desc.setFont(QFont("Segoe UI", 11))
        desc.setStyleSheet(
            f"color: {COLORS['text_secondary']}; padding: 10px 18px;"
            f"background-color: {COLORS['card_bg']};"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        web = QWebEngineView()
        web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        s = web.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        web.setUrl(QUrl.fromLocalFile(os.path.join(_ANIM_DIR, html_file)))
        layout.addWidget(web)


class PhenomenaView(QWidget):
    """Climate Phenomena Lab — tabbed interface hosting interactive animations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title
        title = QLabel("🧪  Climate Phenomena Lab")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(
            f"color: #FFFFFF; padding: 14px 20px;"
            f"background-color: {COLORS['card_bg']};"
        )
        root.addWidget(title)

        # Tab widget
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['background']};
            }}
            QTabBar::tab {{
                background: {COLORS['card_bg']};
                color: {COLORS['text_secondary']};
                padding: 10px 18px;
                margin-right: 2px;
                border: none;
                border-bottom: 3px solid transparent;
                font-size: 13px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                color: #FFFFFF;
                border-bottom: 3px solid #3B82F6;
                background: {COLORS['background']};
            }}
            QTabBar::tab:hover:!selected {{
                color: #E2E8F0;
                background: rgba(255,255,255,0.04);
            }}
        """)

        for label, html_file, description in PHENOMENA:
            page = _AnimationPage(html_file, description)
            tabs.addTab(page, label)

        root.addWidget(tabs)
