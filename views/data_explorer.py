"""
Data Explorer — Interactive environmental data visualization.
Displays 4 factor tabs (CO₂, Renewable Energy, Forest Coverage, Air Pollution),
each with 3 nested chart views (Map, Line Chart, Bar Chart).
All data fetched via DataService, loaded once with QThread, and cached.
"""

import json
import math
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSizePolicy, QSpacerItem, QFrame, QComboBox, QSpinBox,
    QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("QtAgg")

from constants import COLORS
from app_logger import logger

# ── Paths ──
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_MAP_HTML_PATH = os.path.join(_ASSETS_DIR, "choropleth_map.html")
_GEOJSON_PATH = os.path.join(_ASSETS_DIR, "world_geo_min.json")

# ── Cached HTML template + GeoJSON (loaded once) ──
_map_html_template = None
_geojson_raw = None

def _get_map_html_template():
    global _map_html_template
    if _map_html_template is None:
        with open(_MAP_HTML_PATH, "r", encoding="utf-8") as f:
            _map_html_template = f.read()
    return _map_html_template

def _get_geojson_raw():
    """Read world_geo.json once and cache the raw string."""
    global _geojson_raw
    if _geojson_raw is None:
        with open(_GEOJSON_PATH, "r", encoding="utf-8") as f:
            _geojson_raw = f.read()
    return _geojson_raw

# ── Factor definitions ──
FACTORS = [
    {
        "key": "co2_per_capita",
        "label": "CO₂ Emissions",
        "emoji": "🏭",
        "unit": "t CO₂/capita",
        "color": "#EF4444",
    },
    {
        "key": "renewable_percentage",
        "label": "Renewable Energy",
        "emoji": "⚡",
        "unit": "% of total",
        "color": "#22C55E",
    },
    {
        "key": "forest_area_percentage",
        "label": "Forest Coverage",
        "emoji": "🌲",
        "unit": "% of land",
        "color": "#10B981",
    },
    {
        "key": "pm25",
        "label": "Air Pollution",
        "emoji": "💨",
        "unit": "µg/m³ PM2.5",
        "color": "#F59E0B",
    },
]

# ── Color scales for choropleth (threshold, hex color) ──
COLOR_SCALES = {
    "co2_per_capita": [
        [0, "#FEF3C7"], [1, "#FDE68A"], [3, "#FCA5A5"],
        [5, "#F87171"], [8, "#EF4444"], [12, "#DC2626"],
        [20, "#991B1B"], [30, "#7F1D1D"],
    ],
    "renewable_percentage": [
        [0, "#F0FDF4"], [10, "#DCFCE7"], [20, "#BBF7D0"],
        [30, "#86EFAC"], [40, "#4ADE80"], [50, "#22C55E"],
        [60, "#16A34A"], [75, "#15803D"], [90, "#166534"],
    ],
    "forest_area_percentage": [
        [0, "#ECFDF5"], [5, "#D1FAE5"], [15, "#A7F3D0"],
        [25, "#6EE7B7"], [35, "#34D399"], [50, "#10B981"],
        [65, "#059669"], [80, "#047857"],
    ],
    "pm25": [
        [0, "#FFF7ED"], [5, "#FFEDD5"], [10, "#FED7AA"],
        [15, "#FDBA74"], [25, "#FB923C"], [35, "#F97316"],
        [50, "#EA580C"], [75, "#C2410C"], [100, "#9A3412"],
    ],
}


# ══════════════════════════════════════════════════════════
# QThread Worker — loads data once (snapshot + timeseries)
# ══════════════════════════════════════════════════════════

class _DataLoadWorker(QThread):
    """Fetch environmental data + time-series from background thread."""
    finished = Signal(list, dict)   # (snapshot_rows, timeseries_dict)
    error = Signal(str)

    def run(self):
        try:
            from services import DataService
            rows = DataService.get_environmental_data()
            ts = DataService.get_timeseries_data()
            self.finished.emit(rows, ts)
        except Exception as e:
            logger.error("DataLoadWorker error: %s", e)
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════
# Chart Helpers
# ══════════════════════════════════════════════════════════

def _dark_figure(width=8, height=5):
    """Create a matplotlib Figure with dark theme matching the app."""
    fig = Figure(figsize=(width, height), dpi=100)
    fig.set_facecolor(COLORS["background"])
    fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.15)
    return fig


def _style_ax(ax, title=""):
    """Apply dark theme styling to an axes."""
    ax.set_facecolor(COLORS["card_bg"])
    ax.set_title(title, color="white", fontsize=14, fontweight="bold", pad=10)
    ax.tick_params(colors="#94A3B8", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["border"])
    ax.spines["left"].set_color(COLORS["border"])
    ax.xaxis.label.set_color("#94A3B8")
    ax.yaxis.label.set_color("#94A3B8")


def _build_map_view(data, factor):
    """Create a QWebEngineView with Leaflet.js choropleth map."""
    web_view = QWebEngineView()
    web_view.setMinimumHeight(400)

    # Allow local file access (for CSS/JS references in the HTML)
    settings = web_view.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

    try:
        html = _get_map_html_template()

        env_json = json.dumps([
            {"country_code": r["country_code"], "country_name": r["country_name"],
             factor["key"]: r.get(factor["key"]), "year": r.get("year", "")}
            for r in data
        ])

        year = str(data[0]["year"]) if data else "N/A"
        color_scale = json.dumps(COLOR_SCALES.get(factor["key"], [[0, "#94A3B8"]]))

        # Inject GeoJSON inline (avoids fetch() CORS issues with file:// URLs)
        geojson_raw = _get_geojson_raw()

        html = html.replace("__ENV_DATA__", env_json)
        html = html.replace("__GEO_DATA__", geojson_raw)
        html = html.replace("__FACTOR_KEY__", factor["key"])
        html = html.replace("__FACTOR_LABEL__", factor["label"])
        html = html.replace("__FACTOR_UNIT__", factor["unit"])
        html = html.replace("__FACTOR_EMOJI__", factor["emoji"])
        html = html.replace("__COLOR_SCALE__", color_scale)
        html = html.replace("__DATA_YEAR__", year)

        factor_html_path = os.path.join(_ASSETS_DIR, f"map_{factor['key']}.html")
        with open(factor_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        web_view.setUrl(QUrl.fromLocalFile(factor_html_path))

    except Exception as e:
        logger.error("Failed to build map view: %s", e)
        web_view.setHtml(f"<html><body style='background:#0F172A;color:#EF4444;padding:40px;"
                         f"font-family:sans-serif'><h2>Map Error</h2><p>{e}</p></body></html>")

    return web_view


# ══════════════════════════════════════════════════════════
# Time-Series Line Chart Widget
# ══════════════════════════════════════════════════════════

class _TimeSeriesWidget(QWidget):
    """Interactive line chart with country dropdown + year range."""

    def __init__(self, ts_data: dict, factor: dict, parent=None):
        super().__init__(parent)
        self._ts_data = ts_data          # {country_code: [(year, value), ...]}
        self._names = {}                 # filled from parent
        self._factor = factor

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Controls bar ──
        controls = QFrame()
        controls.setFixedHeight(50)
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(16, 0, 16, 0)

        # Country selector
        lbl_country = QLabel("Country:")
        lbl_country.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_country.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(lbl_country)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(220)
        self._combo.setFont(QFont("Segoe UI", 10))
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: #FFFFFF;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['card_bg']};
                color: #FFFFFF;
                selection-background-color: {COLORS['primary']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        ctrl_layout.addWidget(self._combo)

        ctrl_layout.addSpacing(20)

        # Year range — From
        lbl_from = QLabel("From:")
        lbl_from.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_from.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(lbl_from)

        self._spin_from = QSpinBox()
        self._spin_from.setRange(1960, 2024)
        self._spin_from.setValue(1990)
        self._spin_from.setFont(QFont("Segoe UI", 10))
        self._spin_from.setFixedWidth(80)
        self._spin_from.setStyleSheet(self._spin_style())
        ctrl_layout.addWidget(self._spin_from)

        # Year range — To
        lbl_to = QLabel("To:")
        lbl_to.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_to.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(lbl_to)

        self._spin_to = QSpinBox()
        self._spin_to.setRange(1960, 2024)
        self._spin_to.setValue(2024)
        self._spin_to.setFont(QFont("Segoe UI", 10))
        self._spin_to.setFixedWidth(80)
        self._spin_to.setStyleSheet(self._spin_style())
        ctrl_layout.addWidget(self._spin_to)

        ctrl_layout.addStretch()

        # Data point count label
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("Segoe UI", 9))
        self._info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(self._info_label)

        layout.addWidget(controls)

        # ── Chart canvas ──
        self._figure = _dark_figure(10, 5.5)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(380)
        layout.addWidget(self._canvas)

        # ── Populate combo ──
        self._populate_combo()

        # ── Connect signals ──
        self._combo.currentIndexChanged.connect(self._redraw)
        self._spin_from.valueChanged.connect(self._redraw)
        self._spin_to.valueChanged.connect(self._redraw)

        # Initial draw
        self._redraw()

    def set_names(self, names: dict):
        """Set country name lookup dict (called by parent)."""
        self._names = names

    def _populate_combo(self):
        """Fill dropdown with countries that have data for this factor."""
        items = []
        for code, series in self._ts_data.items():
            if series:
                name = self._names.get(code, code)
                items.append((name, code))
        items.sort(key=lambda x: x[0])

        self._combo.blockSignals(True)
        self._combo.clear()
        for name, code in items:
            self._combo.addItem(f"{name}  ({code})", code)

        # Default to first country or USA if available
        usa_idx = next((i for i, (_, c) in enumerate(items) if c == "USA"), -1)
        if usa_idx >= 0:
            self._combo.setCurrentIndex(usa_idx)
        self._combo.blockSignals(False)

    def _redraw(self):
        """Redraw the chart for the currently selected country + year range."""
        code = self._combo.currentData()
        if not code or code not in self._ts_data:
            return

        series = self._ts_data[code]
        year_from = self._spin_from.value()
        year_to = self._spin_to.value()
        if year_from > year_to:
            year_from, year_to = year_to, year_from

        # Filter to year range
        filtered = [(y, v) for y, v in series if year_from <= y <= year_to]

        name = self._names.get(code, code)
        factor = self._factor

        # Update info label
        self._info_label.setText(f"{len(filtered)} data points")

        # ── Draw chart ──
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        _style_ax(ax, f"{factor['emoji']}  {name} — {factor['label']} ({year_from}–{year_to})")

        if not filtered:
            ax.text(0.5, 0.5, "No data for selected range", ha="center", va="center",
                    color="#94A3B8", fontsize=14, transform=ax.transAxes)
            self._canvas.draw_idle()
            return

        years = [y for y, _ in filtered]
        values = [v for _, v in filtered]

        # Main line
        ax.plot(years, values, color=factor["color"], linewidth=2.5, alpha=0.9,
                zorder=3)

        # Data point markers
        ax.scatter(years, values, color=factor["color"], s=30, zorder=4,
                   edgecolors="#FFFFFF", linewidths=0.8, alpha=0.9)

        # Fill area under line
        ax.fill_between(years, values, alpha=0.08, color=factor["color"])

        # Grid
        ax.grid(True, alpha=0.15, color="#94A3B8", linestyle="--")

        # Axis labels
        ax.set_xlabel("Year", fontsize=11)
        ax.set_ylabel(factor["unit"], fontsize=11)

        # X axis — integer ticks
        if len(years) > 1:
            step = max(1, (years[-1] - years[0]) // 10)
            xticks = list(range(years[0], years[-1] + 1, step))
            if years[-1] not in xticks:
                xticks.append(years[-1])
            ax.set_xticks(xticks)

        # Add subtle min/max annotations
        if len(values) >= 2:
            max_idx = values.index(max(values))
            min_idx = values.index(min(values))
            ax.annotate(f"▲ {values[max_idx]:.2f}", (years[max_idx], values[max_idx]),
                        textcoords="offset points", xytext=(0, 12),
                        fontsize=8, color=factor["color"], fontweight="bold",
                        ha="center")
            ax.annotate(f"▼ {values[min_idx]:.2f}", (years[min_idx], values[min_idx]),
                        textcoords="offset points", xytext=(0, -16),
                        fontsize=8, color="#64748B", fontweight="bold",
                        ha="center")

        self._figure.subplots_adjust(left=0.10, right=0.96, top=0.90, bottom=0.14)
        self._canvas.draw_idle()

    def _spin_style(self):
        return f"""
            QSpinBox {{
                background-color: {COLORS['background']};
                color: #FFFFFF;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 6px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
            }}
        """


# ══════════════════════════════════════════════════════════
# Interactive Bar Chart Widget
# ══════════════════════════════════════════════════════════

class _BarChartWidget(QWidget):
    """Interactive horizontal bar chart with Top/Bottom toggle, search, and highlight."""

    _MODE_TOP10 = "top10"
    _MODE_BOT10 = "bot10"
    _MODE_ALL = "all"

    def __init__(self, data: list, factor: dict, parent=None):
        super().__init__(parent)
        self._data = [r for r in data if r.get(factor["key"]) is not None]
        self._factor = factor
        self._mode = self._MODE_TOP10
        self._descending = True
        self._highlighted = None   # country_code to highlight
        self._search_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Controls bar ──
        controls = QFrame()
        controls.setFixedHeight(50)
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(12, 0, 12, 0)

        # Mode buttons
        self._btn_top = self._make_toggle_btn("▲ Top 10", True)
        self._btn_bot = self._make_toggle_btn("▼ Bottom 10", False)
        self._btn_all = self._make_toggle_btn("All", False)
        ctrl_layout.addWidget(self._btn_top)
        ctrl_layout.addWidget(self._btn_bot)
        ctrl_layout.addWidget(self._btn_all)

        self._btn_top.clicked.connect(lambda: self._set_mode(self._MODE_TOP10))
        self._btn_bot.clicked.connect(lambda: self._set_mode(self._MODE_BOT10))
        self._btn_all.clicked.connect(lambda: self._set_mode(self._MODE_ALL))

        ctrl_layout.addSpacing(12)

        # Sort toggle
        self._btn_sort = QPushButton("⇅ Descending")
        self._btn_sort.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self._btn_sort.setCursor(Qt.PointingHandCursor)
        self._btn_sort.setFixedHeight(30)
        self._btn_sort.setStyleSheet(self._ctrl_btn_style(False))
        self._btn_sort.clicked.connect(self._toggle_sort)
        ctrl_layout.addWidget(self._btn_sort)

        ctrl_layout.addSpacing(16)

        # Search field
        lbl_search = QLabel("🔍")
        lbl_search.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(lbl_search)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search country...")
        self._search.setFont(QFont("Segoe UI", 10))
        self._search.setFixedWidth(180)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                color: #FFFFFF;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
            }}
        """)
        self._search.textChanged.connect(self._on_search)
        ctrl_layout.addWidget(self._search)

        ctrl_layout.addStretch()

        # Info label
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("Segoe UI", 9))
        self._info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        ctrl_layout.addWidget(self._info_label)

        layout.addWidget(controls)

        # ── Chart canvas ──
        self._figure = _dark_figure(10, 6)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(380)
        self._canvas.mpl_connect("button_press_event", self._on_click)
        layout.addWidget(self._canvas)

        # Store bar positions for click detection
        self._bar_codes = []

        # Initial draw
        self._redraw()

    # ── Mode / Sort ──

    def _set_mode(self, mode):
        self._mode = mode
        self._btn_top.setStyleSheet(self._ctrl_btn_style(mode == self._MODE_TOP10))
        self._btn_bot.setStyleSheet(self._ctrl_btn_style(mode == self._MODE_BOT10))
        self._btn_all.setStyleSheet(self._ctrl_btn_style(mode == self._MODE_ALL))
        self._redraw()

    def _toggle_sort(self):
        self._descending = not self._descending
        self._btn_sort.setText("⇅ Descending" if self._descending else "⇅ Ascending")
        self._redraw()

    def _on_search(self, text):
        self._search_text = text.strip().lower()
        self._redraw()

    def _on_click(self, event):
        """Highlight the clicked bar's country."""
        if event.inaxes is None or not self._bar_codes:
            return
        # Find which bar was clicked (by y position)
        y = event.ydata
        if y is None:
            return
        idx = int(round(y))
        if 0 <= idx < len(self._bar_codes):
            code = self._bar_codes[idx]
            self._highlighted = code if self._highlighted != code else None
            self._redraw()

    # ── Drawing ──

    def _redraw(self):
        factor = self._factor
        key = factor["key"]

        # Sort data
        sorted_data = sorted(self._data, key=lambda r: r[key], reverse=self._descending)

        # Filter by search
        if self._search_text:
            sorted_data = [
                r for r in sorted_data
                if self._search_text in r["country_name"].lower()
                or self._search_text in r["country_code"].lower()
            ]

        # Slice by mode
        if self._mode == self._MODE_TOP10:
            display = sorted_data[:10]
        elif self._mode == self._MODE_BOT10:
            display = sorted_data[-10:] if len(sorted_data) >= 10 else sorted_data
        else:
            display = sorted_data[:30]  # cap at 30 for readability

        # Reverse for horizontal bar (top = first item)
        display = list(reversed(display))

        self._info_label.setText(f"{len(display)} of {len(self._data)} countries")

        # ── Draw ──
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        mode_label = {self._MODE_TOP10: "Top 10", self._MODE_BOT10: "Bottom 10", self._MODE_ALL: "All Countries"}[self._mode]
        order_label = "Descending" if self._descending else "Ascending"
        _style_ax(ax, f"{factor['emoji']}  {factor['label']} — {mode_label} ({order_label})")

        if not display:
            ax.text(0.5, 0.5, "No matching countries", ha="center", va="center",
                    color="#94A3B8", fontsize=14, transform=ax.transAxes)
            self._bar_codes = []
            self._canvas.draw_idle()
            return

        names = [r["country_name"][:20] for r in display]
        values = [r[key] for r in display]
        codes = [r["country_code"] for r in display]
        self._bar_codes = codes

        # Colors — highlighted country gets bright border
        bar_colors = []
        edge_colors = []
        edge_widths = []
        for r in display:
            if r["country_code"] == self._highlighted:
                bar_colors.append("#FFFFFF")
                edge_colors.append(factor["color"])
                edge_widths.append(2.5)
            else:
                bar_colors.append(factor["color"])
                edge_colors.append("#334155")
                edge_widths.append(0.8)

        y_pos = range(len(display))
        bars = ax.barh(y_pos, values, color=bar_colors, alpha=0.85,
                       edgecolor=edge_colors, linewidth=edge_widths, height=0.7)

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(names, fontsize=9)
        ax.set_xlabel(factor["unit"], fontsize=10)

        # Value labels
        max_val = max(values) if values else 1
        for i, (bar, val, r) in enumerate(zip(bars, values, display)):
            label_color = factor["color"] if r["country_code"] == self._highlighted else "#94A3B8"
            ax.text(bar.get_width() + max_val * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f'{val:.2f}', va="center", color=label_color,
                    fontsize=8, fontweight="bold" if r["country_code"] == self._highlighted else "normal")

        ax.grid(True, axis="x", alpha=0.1, color="#94A3B8", linestyle="--")

        self._figure.subplots_adjust(left=0.22, right=0.96, top=0.92, bottom=0.10)
        self._canvas.draw_idle()

    # ── Helpers ──

    def _make_toggle_btn(self, text, active):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet(self._ctrl_btn_style(active))
        return btn

    def _ctrl_btn_style(self, active):
        if active:
            return f"""
                QPushButton {{
                    background-color: {self._factor['color']}25;
                    color: {self._factor['color']};
                    border: 1px solid {self._factor['color']};
                    border-radius: 6px;
                    padding: 4px 12px;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                color: #FFFFFF;
                border-color: {COLORS['text_secondary']};
            }}
        """


# ══════════════════════════════════════════════════════════
# Main Widget
# ══════════════════════════════════════════════════════════

class DataExplorerWidget(QWidget):
    """Data Explorer with 4 factor tabs, each containing Map/Line/Bar views."""

    def __init__(self, user_id=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self._cache = []
        self._ts_cache = {}
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet(f"background-color: {COLORS['card_bg']};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("📊  Data Explorer")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        h_layout.addWidget(title)

        h_layout.addStretch()


        self._status_label = QLabel("")
        self._status_label.setFont(QFont("Segoe UI", 11))
        self._status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        h_layout.addWidget(self._status_label)

        layout.addWidget(header)

        # ── Loading placeholder ──
        self._loading_label = QLabel("⏳ Fetching environmental data...")
        self._loading_label.setFont(QFont("Segoe UI", 14))
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 40px;")
        layout.addWidget(self._loading_label)

        # ── Factor Tabs (created after data loads) ──
        self._tab_widget = None

        # Start loading
        self._load_data()

    def _load_data(self):
        """Fetch data via QThread."""
        self._worker = _DataLoadWorker()
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_error(self, msg):
        self._loading_label.setText(f"❌ Error loading data: {msg}")
        self._status_label.setText("Error")

    def _on_data_loaded(self, rows, ts_data):
        """Build the full tabbed UI once data is available."""
        self._cache = rows
        self._ts_cache = ts_data
        self._loading_label.setVisible(False)

        count = len(rows)
        year = rows[0]["year"] if rows else "N/A"

        # ── Create Factor Tabs ──
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(self._tab_style())
        self._tab_widget.setDocumentMode(True)

        for factor in FACTORS:
            factor_tab = self._build_factor_tab(factor)
            self._tab_widget.addTab(factor_tab, f"  {factor['emoji']}  {factor['label']}  ")

        self.layout().addWidget(self._tab_widget)

    def _build_factor_tab(self, factor):
        """Build a single factor tab with 3 nested view tabs."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary stat bar
        valid_count = sum(1 for r in self._cache if r.get(factor["key"]) is not None)
        values = [r[factor["key"]] for r in self._cache if r.get(factor["key"]) is not None]
        avg_val = sum(values) / len(values) if values else 0
        max_val = max(values) if values else 0
        min_val = min(values) if values else 0

        stats_bar = QFrame()
        stats_bar.setFixedHeight(50)
        stats_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(20, 0, 20, 0)

        for label, value in [("Countries", f"{valid_count}"),
                             ("Average", f"{avg_val:.2f}"),
                             ("Highest", f"{max_val:.2f}"),
                             ("Lowest", f"{min_val:.2f}")]:
            pill = QLabel(f"  {label}: {value}  ")
            pill.setFont(QFont("Segoe UI", 10, QFont.Bold))
            pill.setStyleSheet(f"""
                color: {factor['color']};
                background-color: {factor['color']}15;
                border-radius: 8px;
                padding: 4px 10px;
                border: none;
            """)
            stats_layout.addWidget(pill)

        stats_layout.addStretch()
        layout.addWidget(stats_bar)

        # ── View Tabs (Map / Line / Bar) ──
        view_tabs = QTabWidget()
        view_tabs.setStyleSheet(self._view_tab_style())
        view_tabs.setDocumentMode(True)

        # Map View (Leaflet choropleth)
        map_view = _build_map_view(self._cache, factor)
        view_tabs.addTab(map_view, "  🗺  Map View  ")

        # Line Chart (interactive time-series)
        ts_factor_data = self._ts_cache.get(factor["key"], {})
        ts_names = self._ts_cache.get("_names", {})
        ts_widget = _TimeSeriesWidget(ts_factor_data, factor)
        ts_widget.set_names(ts_names)
        ts_widget._populate_combo()   # re-populate with names now available
        ts_widget._redraw()
        view_tabs.addTab(ts_widget, "  📈  Line Chart  ")

        # Bar Chart (interactive)
        bar_widget = _BarChartWidget(self._cache, factor)
        view_tabs.addTab(bar_widget, "  📊  Bar Chart  ")

        layout.addWidget(view_tabs)
        return container

    # ── Stylesheet helpers ──

    def _tab_style(self):
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['background']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['card_bg']};
                color: {COLORS['text_secondary']};
                padding: 10px 18px;
                margin-right: 2px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 13px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['primary']};
                border-bottom: 2px solid {COLORS['primary']};
                background-color: {COLORS['background']};
            }}
            QTabBar::tab:hover {{
                color: #FFFFFF;
                background-color: {COLORS['border']};
            }}
        """

    def _view_tab_style(self):
        return f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['background']};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                padding: 8px 16px;
                margin-right: 2px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['secondary']};
                border-bottom: 2px solid {COLORS['secondary']};
            }}
            QTabBar::tab:hover {{
                color: #FFFFFF;
            }}
        """
