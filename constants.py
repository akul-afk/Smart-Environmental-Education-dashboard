"""
Constants and configuration for the Smart Environmental Education app.
Qt-compatible color strings and settings.
"""

from PySide6.QtGui import QColor

# Color Palette (hex strings — Qt accepts these directly)
COLORS = {
    "background": "#0F172A",      # Deep Slate
    "card_bg": "#1E293B",         # Slate
    "primary": "#22C55E",         # Neon Green
    "secondary": "#3B82F6",       # Blue
    "tertiary": "#F59E0B",        # Amber
    "text_secondary": "#94A3B8",  # Gray
    "border": "#334155",          # Border Gray
    # XP & Gamification colors
    "xp_gold": "#FFD700",         # Gold for XP
    "xp_bar_bg": "#374151",       # Dark bar background
    "level_purple": "#A855F7",    # Purple for level up
    "streak_orange": "#F97316",   # Orange for streak flame
    "badge_beginner": "#86EFAC",  # Light green
    "badge_growth": "#34D399",    # Medium green
    "badge_impact": "#2563EB",    # Bold blue
    "badge_analyst": "#8B5CF6",   # Violet
    "danger": "#EF4444",          # Red for caps/limits
}

# Animation Settings
ANIMATION = {
    "button_duration": 300,
    "transition_duration": 400,
    "button_scale": 1.05,
}

# Window Settings
WINDOW = {
    "min_width": 900,
    "min_height": 600,
}

# XP Action Types & Base Values
XP_VALUES = {
    "lesson_complete": 50,
    "lesson_advanced": 75,
    "visualization_watch": 20,
    "quiz_attempt": 10,
    "quiz_correct": 15,
    "quiz_perfect": 40,
    "challenge_complete": 30,
    "streak_7_bonus": 100,
    "carbon_calc_first": 25,
    "carbon_calc_improve": 30,
    "simulation_high": 80,
    "simulation_co2_reduce": 60,
}


def qcolor(hex_str: str) -> QColor:
    """Helper to create QColor from hex string."""
    return QColor(hex_str)


# Global stylesheet for the dark theme
GLOBAL_STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {COLORS['background']};
        color: #FFFFFF;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
    }}
    QLabel {{
        color: #FFFFFF;
    }}
    QLineEdit {{
        background-color: {COLORS['background']};
        color: #FFFFFF;
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border: 1.5px solid {COLORS['primary']};
    }}
    QPushButton {{
        background-color: {COLORS['card_bg']};
        color: #FFFFFF;
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        border: 1px solid {COLORS['primary']};
        background-color: #253349;
    }}
    QPushButton:pressed {{
        background-color: #1a2a3f;
    }}
    QProgressBar {{
        background-color: {COLORS['xp_bar_bg']};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS['primary']};
        border-radius: 4px;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background-color: {COLORS['background']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""
