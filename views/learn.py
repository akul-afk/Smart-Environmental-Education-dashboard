"""
Learn View — Knowledge Biomes browser.
Loads 4 biomes from the database via DataService (no hardcoded data).
PySide6 + QThread for non-blocking loading.
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea, QGridLayout,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QColor, QIcon

from constants import COLORS, XP_VALUES
from app_logger import logger

# Resolve assets directory relative to project root
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
BACK_ICON_PATH = os.path.join(ASSETS_DIR, "icons", "ui", "back_arrow.png")


# ── Workers ──

class _BiomesLoadWorker(QThread):
    """Background worker for loading biomes from DB."""
    finished = Signal(list)

    def run(self):
        from services import DataService
        biomes = DataService.get_all_biomes()
        # Enrich each biome with total XP from its lessons
        for biome in biomes:
            lessons = DataService.get_lessons_by_biome(biome["slug"])
            total_xp = sum(l.get("xp_reward", 50) for l in lessons)
            biome["_total_xp"] = total_xp
            biome["_lesson_count"] = len(lessons)
        self.finished.emit(biomes)


class _LessonsLoadWorker(QThread):
    """Background worker for loading lessons for a biome."""
    finished = Signal(list)

    def __init__(self, biome_slug):
        super().__init__()
        self.biome_slug = biome_slug

    def run(self):
        from services import DataService
        lessons = DataService.get_lessons_by_biome(self.biome_slug)
        self.finished.emit(lessons)


class _LearnXPWorker(QThread):
    """Background worker for awarding lesson XP."""
    finished = Signal(str)

    def __init__(self, user_id, biome_name, biome_slug, base_xp=50, difficulty="beginner"):
        super().__init__()
        self.user_id = user_id
        self.biome_name = biome_name
        self.biome_slug = biome_slug
        self.base_xp = base_xp
        self.difficulty = difficulty

    def run(self):
        from services import DataService
        try:
            result = DataService.award_xp(
                self.user_id, "lesson_complete",
                self.base_xp,
                source_ref_id=self.biome_slug,
                difficulty=self.difficulty,
            )
            if result.get("xp_earned", 0) > 0:
                DataService.increment_progress(self.user_id, "lessons_completed")

            parts = []
            if result.get("xp_earned", 0) > 0:
                parts.append(f"⚡ +{result['xp_earned']} XP earned!")
            if result.get("leveled_up"):
                parts.append(f"🎉 Level {result['level']}!")
            if result.get("new_badges"):
                for b in result["new_badges"]:
                    parts.append(f"🏆 Badge: {b['name']}!")
            if result.get("capped"):
                parts.append(f"({result.get('reason', 'XP capped')})")

            msg = "  ".join(parts) if parts else f"✅ {self.biome_name} explored!"
            self.finished.emit(msg)
        except Exception as e:
            logger.error("Learn XP error: %s", e)
            self.finished.emit(f"✅ {self.biome_name} explored!")


# ── Biome Card Widget ──

class _BiomeCard(QFrame):
    """A single biome card with glassmorphism styling and hover elevation."""

    def __init__(self, biome: dict, on_click=None, parent=None):
        super().__init__(parent)
        self.biome = biome
        self.on_click = on_click
        self._hovered = False

        color = biome.get("theme_color", COLORS["primary"])
        self.accent_color = color
        
        slug = biome.get("slug", "")
        if slug == "blue_sphere":
            self.card_bg = "assets/textures/cards/biome_ocean_card.png"
            self.icon_path = "assets/icons/biomes/biome_ocean_icon.png"
        elif slug == "green_lungs":
            self.card_bg = "assets/textures/cards/biome_forest_card.png"
            self.icon_path = "assets/icons/biomes/biome_forest_icon.png"
        elif slug == "energy_grid":
            self.card_bg = "assets/textures/cards/biome_energy_card.png"
            self.icon_path = "assets/icons/biomes/biome_energy_icon.png"
        elif slug == "circular_economy":
            self.card_bg = "assets/textures/cards/biome_recycle_card.png"
            self.icon_path = "assets/icons/biomes/biome_recycle_icon.png"
        else:
            self.card_bg = ""
            self.icon_path = ""

        self.setFixedSize(340, 340)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("BiomeCardFrame")
        self._apply_style(hovered=False)

        # Drop shadow for hover elevation
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(color))
        self.setGraphicsEffect(self._shadow)

        self._build_layout(biome)

    def _apply_style(self, hovered: bool):
        color = self.accent_color
        border = f"2px solid {color}" if hovered else f"1px solid {COLORS['border']}"
        
        # Combine the texture image with a dark gradient overlay
        if self.card_bg:
            bg_rule = (
                f"border-image: url('{self.card_bg}') 0 0 0 0 stretch stretch;"
            )
            # To add an overlay on top of border-image in PySide safely, we often need multiple drawing passes,
            # but setting a background-color with transparency over a border-image achieves the dark overlay!
            overlay_rule = "background-color: rgba(11, 25, 40, 0.65);"
        else:
            bg_rule = f"background-color: {COLORS['card_bg']};"
            overlay_rule = ""

        self.setStyleSheet(f"""
            QFrame#BiomeCardFrame {{
                {bg_rule}
                {overlay_rule}
                border: {border};
                border-radius: 16px;
            }}
        """)

    def _build_layout(self, biome):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Dark overlay container for text readability
        overlay = QFrame()
        overlay.setStyleSheet("QFrame { background-color: rgba(11, 31, 46, 0.65); border-radius: 16px; border: none; }")
        col = QVBoxLayout(overlay)
        col.setContentsMargins(20, 20, 20, 16)
        col.setSpacing(0)

        # Icon as QPixmap instead of Emoji
        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        if self.icon_path and os.path.exists(self.icon_path):
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(self.icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pixmap)
        else:
            icon.setText(biome.get("icon_name", "🌍"))
            icon.setFont(QFont("Segoe UI Emoji", 36))
        
        col.addWidget(icon)

        col.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Name
        name = QLabel(biome["name"])
        name.setFont(QFont("Segoe UI", 18, QFont.Bold))
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: #FFFFFF; border: none; background: transparent;")
        col.addWidget(name)

        col.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Description (truncated)
        desc_text = biome.get("short_description", "")
        if len(desc_text) > 110:
            desc_text = desc_text[:107] + "..."
        desc = QLabel(desc_text)
        desc.setFont(QFont("Segoe UI", 11))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(f"color: #E2E8F0; border: none; background: transparent;")
        col.addWidget(desc)

        col.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Info row: difficulty + time
        info_row = QHBoxLayout()
        info_row.setSpacing(10)

        diff = biome.get("difficulty_level", "beginner")
        diff_map = {
            "beginner": ("🟢 Beginner", COLORS["primary"]),
            "intermediate": ("🟡 Intermediate", COLORS["tertiary"]),
            "advanced": ("🔴 Advanced", "#EF4444"),
        }
        diff_text, diff_color = diff_map.get(diff, ("🟢 Beginner", COLORS["primary"]))

        diff_label = QLabel(diff_text)
        diff_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        diff_label.setStyleSheet(f"color: {diff_color}; border: none; background: transparent;")
        info_row.addWidget(diff_label)

        info_row.addStretch()

        mins = biome.get("estimated_minutes", 30)
        time_label = QLabel(f"⏱ {mins} min")
        time_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
        info_row.addWidget(time_label)

        col.addLayout(info_row)

        col.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # XP preview — compute total XP available for this biome from DB lessons
        total_xp = biome.get("_total_xp", 0)
        lesson_count = biome.get("_lesson_count", 0)
        if total_xp > 0 and lesson_count > 0:
            xp_text = f"⚡ {total_xp} XP  ({lesson_count} lessons)"
        else:
            xp_text = f"⚡ {XP_VALUES['lesson_complete']} XP/lesson"
        xp_label = QLabel(xp_text)
        xp_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        xp_label.setAlignment(Qt.AlignCenter)
        xp_label.setStyleSheet(f"color: {COLORS['xp_gold']}; border: none; background: transparent;")
        col.addWidget(xp_label)

        col.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Explore button
        color = biome.get("theme_color", COLORS["primary"])
        btn = QPushButton("Explore →")
        btn.setFixedHeight(40)
        btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #FFFFFF;
                border: none; border-radius: 10px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(lambda: self.on_click(biome) if self.on_click else None)
        col.addWidget(btn)
        
        layout.addWidget(overlay)

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style(hovered=True)
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 4)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style(hovered=False)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.biome)
        super().mousePressEvent(event)


# ── Main Widget ──

class LearnWidget(QWidget):
    """Learn View — Knowledge Biomes loaded from DB via DataService."""

    def __init__(self, user_id=1, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self._load_worker = None
        self._xp_worker = None
        self._lessons_worker = None

        self._stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        
        # Apply the glowing Learn-specific background
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            LearnWidget {{
                border-image: url('assets/textures/backgrounds/learn_tab_bg.png') 0 0 0 0 stretch stretch;
            }}
        """)

        self._show_loading()
        self._load_biomes()

    def _clear_and_set(self, widget):
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    # ── Loading State ──
    def _show_loading(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        spinner = QLabel("⏳ Loading Knowledge Biomes...")
        spinner.setFont(QFont("Segoe UI", 16))
        spinner.setAlignment(Qt.AlignCenter)
        spinner.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(spinner)

        self._clear_and_set(page)

    def _load_biomes(self):
        self._load_worker = _BiomesLoadWorker()
        self._load_worker.finished.connect(self._on_biomes_loaded)
        self._load_worker.start()

    def _on_biomes_loaded(self, biomes):
        if not biomes:
            self._show_error()
            return
        self._show_biome_grid(biomes)

    # ── Error State ──
    def _show_error(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        msg = QLabel("⚠️ Could not load biomes. Please check your database connection.")
        msg.setFont(QFont("Segoe UI", 14))
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {COLORS['tertiary']};")
        layout.addWidget(msg)

        retry_btn = QPushButton("🔄  Retry")
        retry_btn.setFixedSize(120, 40)
        retry_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        retry_btn.setCursor(Qt.PointingHandCursor)
        retry_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}; color: #FFFFFF;
                border: none; border-radius: 10px;
            }}
            QPushButton:hover {{ background-color: #1aaf4f; }}
        """)
        retry_btn.clicked.connect(self._load_biomes)
        layout.addWidget(retry_btn, alignment=Qt.AlignCenter)

        self._clear_and_set(page)

    # ── Biome Grid ──
    def _show_biome_grid(self, biomes):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # Header
        title = QLabel("🌍 Knowledge Biomes")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setStyleSheet("""
            color: #FFFFFF; 
            background: transparent;
        """)
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        subtitle = QLabel("Explore the four pillars of environmental science. Each biome is a self-contained learning world.")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9); 
            background: transparent;
        """)
        layout.addWidget(subtitle)

        layout.addSpacerItem(QSpacerItem(0, 25, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Card Grid (2×2)
        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setAlignment(Qt.AlignCenter)

        for i, biome in enumerate(biomes):
            card = _BiomeCard(biome, on_click=self._on_biome_click)
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(content)
        self._clear_and_set(scroll)

    # ── Biome Detail — show lessons ──
    def _on_biome_click(self, biome):
        """Load lessons for the clicked biome from DB."""
        self._current_biome = biome
        # Show loading while fetching lessons
        loading = QWidget()
        ll = QVBoxLayout(loading)
        ll.setAlignment(Qt.AlignCenter)
        spin = QLabel(f"⏳ Loading {biome['name']} lessons...")
        spin.setFont(QFont("Segoe UI", 16))
        spin.setAlignment(Qt.AlignCenter)
        spin.setStyleSheet(f"color: {COLORS['text_secondary']};")
        ll.addWidget(spin)
        self._clear_and_set(loading)

        self._lessons_worker = _LessonsLoadWorker(biome["slug"])
        self._lessons_worker.finished.connect(
            lambda lessons: self._show_biome_lessons(biome, lessons)
        )
        self._lessons_worker.start()

    def _show_biome_lessons(self, biome, lessons):
        """Display the list of lessons for a biome."""
        import json as _json
        color = biome.get("theme_color", COLORS["primary"])

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # Header with back button
        header = QHBoxLayout()

        back_btn = QPushButton()
        back_btn.setFixedSize(40, 40)
        back_btn.setIcon(QIcon(BACK_ICON_PATH))
        back_btn.setIconSize(QSize(36, 36))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover { opacity: 0.85; }
        """)
        back_btn.clicked.connect(self._load_biomes)
        header.addWidget(back_btn)

        icon = QLabel(biome.get("icon_name", "🌍"))
        icon.setFont(QFont("Segoe UI Emoji", 24))
        header.addWidget(icon)

        title = QLabel(biome["name"])
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        header.addWidget(title)

        header.addStretch()
        layout.addLayout(header)

        layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Biome description
        desc = QLabel(biome.get("short_description", ""))
        desc.setFont(QFont("Segoe UI", 13))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(desc)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        if not lessons:
            empty = QLabel("No lessons available yet for this biome.")
            empty.setFont(QFont("Segoe UI", 14))
            empty.setStyleSheet(f"color: {COLORS['text_secondary']};")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        else:
            # Lesson header
            lesson_header = QLabel(f"📖  {len(lessons)} Lessons")
            lesson_header.setFont(QFont("Segoe UI", 16, QFont.Bold))
            lesson_header.setStyleSheet("color: #FFFFFF;")
            layout.addWidget(lesson_header)

            layout.addSpacerItem(QSpacerItem(0, 14, QSizePolicy.Minimum, QSizePolicy.Fixed))

            # Lesson cards
            for i, lesson in enumerate(lessons):
                card = self._lesson_card(lesson, i + 1, color)
                layout.addWidget(card)
                layout.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))

        layout.addStretch()
        scroll.setWidget(content)
        self._clear_and_set(scroll)

    def _lesson_card(self, lesson, number, accent_color):
        """Build a card for a single lesson."""
        frame = QFrame()
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {accent_color};
            }}
        """)

        row = QHBoxLayout(frame)
        row.setContentsMargins(18, 16, 18, 16)
        row.setSpacing(14)

        # Number circle
        num_label = QLabel(str(number))
        num_label.setFixedSize(36, 36)
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        num_label.setStyleSheet(f"""
            color: {accent_color};
            background-color: {accent_color}22;
            border-radius: 18px;
            border: none;
        """)
        row.addWidget(num_label)

        # Title + meta
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        title = QLabel(lesson["title"])
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        title.setWordWrap(True)
        text_col.addWidget(title)

        diff = lesson.get("difficulty", "beginner")
        diff_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(diff, "🟢")
        meta = QLabel(f"{diff_emoji} {diff.capitalize()}  ·  ⏱ {lesson.get('estimated_minutes', 10)} min  ·  ⚡ {lesson.get('xp_reward', 50)} XP")
        meta.setFont(QFont("Segoe UI", 10))
        meta.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
        text_col.addWidget(meta)

        row.addLayout(text_col, stretch=1)

        # Open button
        open_btn = QPushButton("Open →")
        open_btn.setFixedSize(80, 34)
        open_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color}; color: #FFFFFF;
                border: none; border-radius: 10px;
            }}
            QPushButton:hover {{ background-color: {accent_color}cc; }}
        """)
        open_btn.clicked.connect(lambda _, l=lesson: self._show_lesson_content(l))
        row.addWidget(open_btn)

        return frame

    # ── Lesson Content Viewer ──

    def _show_lesson_content(self, lesson):
        """Render full lesson content from content_json."""
        import json as _json

        biome = getattr(self, "_current_biome", {})
        color = biome.get("theme_color", COLORS["primary"])

        # Parse content_json
        content_data = lesson.get("content_json", "{}")
        if isinstance(content_data, str):
            try:
                content_data = _json.loads(content_data)
            except _json.JSONDecodeError:
                content_data = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # Header with back button
        header = QHBoxLayout()

        back_btn = QPushButton()
        back_btn.setFixedSize(40, 40)
        back_btn.setIcon(QIcon(BACK_ICON_PATH))
        back_btn.setIconSize(QSize(36, 36))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover { opacity: 0.85; }
        """)
        back_btn.clicked.connect(lambda: self._on_biome_click(biome))
        header.addWidget(back_btn)

        title = QLabel(lesson["title"])
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        title.setWordWrap(True)
        header.addWidget(title, stretch=1)

        header.addStretch()
        layout.addLayout(header)

        layout.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Meta pills
        diff = lesson.get("difficulty", "beginner")
        diff_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(diff, "🟢")
        meta = QLabel(f"{diff_emoji} {diff.capitalize()}  ·  ⏱ {lesson.get('estimated_minutes', 10)} min  ·  ⚡ {lesson.get('xp_reward', 50)} XP")
        meta.setFont(QFont("Segoe UI", 12))
        meta.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(meta)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Learning Objectives ──
        objectives = content_data.get("learning_objectives", [])
        if objectives:
            obj_frame = QFrame()
            obj_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {color}15;
                    border: 1px solid {color}44;
                    border-radius: 14px;
                }}
            """)
            obj_layout = QVBoxLayout(obj_frame)
            obj_layout.setContentsMargins(20, 16, 20, 16)
            obj_layout.setSpacing(6)

            obj_title = QLabel("🎯 Learning Objectives")
            obj_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
            obj_title.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            obj_layout.addWidget(obj_title)

            for obj in objectives:
                obj_label = QLabel(f"  •  {obj}")
                obj_label.setFont(QFont("Segoe UI", 11))
                obj_label.setWordWrap(True)
                obj_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
                obj_layout.addWidget(obj_label)

            layout.addWidget(obj_frame)
            layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Content Sections ──
        sections = content_data.get("sections", [])
        for i, section in enumerate(sections):
            # Section title
            sec_title = section.get("title", f"Section {i + 1}")
            sec_label = QLabel(sec_title)
            sec_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
            sec_label.setStyleSheet(f"color: {color};")
            layout.addWidget(sec_label)

            layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

            # Section content
            sec_content = section.get("content", "")
            content_label = QLabel(sec_content)
            content_label.setFont(QFont("Segoe UI", 12))
            content_label.setWordWrap(True)
            content_label.setStyleSheet(f"color: {COLORS['text_secondary']}; line-height: 1.6;")
            layout.addWidget(content_label)

            layout.addSpacerItem(QSpacerItem(0, 18, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Real-World Example ──
        example = content_data.get("real_world_example", "")
        if example:
            ex_frame = QFrame()
            ex_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['card_bg']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 14px;
                }}
            """)
            ex_layout = QVBoxLayout(ex_frame)
            ex_layout.setContentsMargins(20, 16, 20, 16)
            ex_layout.setSpacing(6)

            ex_title = QLabel("🌍 Real-World Example")
            ex_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
            ex_title.setStyleSheet(f"color: {COLORS['tertiary']}; border: none; background: transparent;")
            ex_layout.addWidget(ex_title)

            ex_text = QLabel(example)
            ex_text.setFont(QFont("Segoe UI", 12))
            ex_text.setWordWrap(True)
            ex_text.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
            ex_layout.addWidget(ex_text)

            layout.addWidget(ex_frame)
            layout.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Complete Lesson Button ──
        complete_btn = QPushButton(f"✅  Complete Lesson  ·  +{lesson.get('xp_reward', 50)} XP")
        complete_btn.setFixedHeight(50)
        complete_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        complete_btn.setCursor(Qt.PointingHandCursor)
        complete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #FFFFFF;
                border: none; border-radius: 14px;
            }}
            QPushButton:hover {{ background-color: {color}cc; }}
        """)
        complete_btn.clicked.connect(
            lambda: self._complete_lesson(lesson, biome, complete_btn)
        )
        layout.addWidget(complete_btn)

        layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # XP feedback label (hidden until completion)
        self._xp_feedback = QLabel("")
        self._xp_feedback.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._xp_feedback.setAlignment(Qt.AlignCenter)
        self._xp_feedback.setStyleSheet(f"color: {COLORS['xp_gold']};")
        self._xp_feedback.setVisible(False)
        layout.addWidget(self._xp_feedback)

        layout.addStretch()
        scroll.setWidget(page)
        self._clear_and_set(scroll)

    def _complete_lesson(self, lesson, biome, btn):
        """Award XP for completing a lesson."""
        btn.setEnabled(False)
        btn.setText("⏳ Awarding XP...")

        xp = lesson.get("xp_reward", XP_VALUES["lesson_complete"])
        diff = lesson.get("difficulty", "beginner")
        slug = lesson.get("lesson_slug", biome.get("slug", "unknown"))

        self._xp_worker = _LearnXPWorker(
            self.user_id, lesson["title"], slug,
            base_xp=xp, difficulty=diff,
        )
        self._xp_worker.finished.connect(
            lambda msg: self._on_lesson_completed(msg, btn)
        )
        self._xp_worker.start()

    def _on_lesson_completed(self, msg, btn):
        """Show XP feedback after lesson completion."""
        btn.setText("✅ Completed!")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}44; color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "_xp_feedback") and self._xp_feedback:
            self._xp_feedback.setText(msg)
            self._xp_feedback.setVisible(True)

