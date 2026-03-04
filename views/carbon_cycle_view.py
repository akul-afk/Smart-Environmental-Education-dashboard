"""
Carbon Cycle View — PySide6 integration for the static SVG animation.

This view simply loads the locally provided SVG animation HTML file
into a full-container QWebEngineView.
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings


# ── Path to the HTML asset (resolved relative to project root) ──
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_HTML_PATH = os.path.join(_ASSETS_DIR, "carbon_cycle.html")


class CarbonCycleView(QWidget):
    """Interactive carbon cycle SVG animation viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── QWebEngineView ──
        self._web = QWebEngineView()
        self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Allow local files to access local assets if needed
        settings = self._web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        # Load the HTML file directly
        self._web.setUrl(QUrl.fromLocalFile(_HTML_PATH))

        root.addWidget(self._web)
