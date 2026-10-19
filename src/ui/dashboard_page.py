"""
LOG NEST - Dashboard Page
Main dashboard with statistics cards, activity chart, and recent events.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QStackedWidget,
    QPushButton
)
from PySide6.QtCore import Qt, QTimer, Slot

from src.database import DatabaseManager
from src.ui.theme import COLORS
from src.ui.widgets import StatCard, EventCard, ActivityChart, PulsingDot
from src.ui.digital_wellbeing_page import DigitalWellbeingPage


class DashboardPage(QWidget):
    """Dashboard page with live statistics and recent activity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._current_view_idx = 0
        self._setup_ui()

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start(5000)  # Refresh every 5 seconds

        # Initial load
        QTimer.singleShot(100, self.refresh_data)

    def _setup_ui(self):
        """Build the dashboard UI with segmented view switcher."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ─── Navigation Header with View Switcher ────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        # Segmented view switcher: [ 🌿 Digital Wellbeing ] [ 📊 System Activity ]
        switcher_frame = QFrame()
        switcher_frame.setStyleSheet(
            f"background-color: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; padding: 2px;"
        )
        switcher_layout = QHBoxLayout(switcher_frame)
        switcher_layout.setContentsMargins(2, 2, 2, 2)
        switcher_layout.setSpacing(4)

        self.btn_tab_wellbeing = QPushButton("🌿  Digital Wellbeing")
        self.btn_tab_wellbeing.setCursor(Qt.PointingHandCursor)
        self.btn_tab_wellbeing.clicked.connect(lambda: self._switch_view(0))
        switcher_layout.addWidget(self.btn_tab_wellbeing)

        self.btn_tab_activity = QPushButton("📊  System Activity")
        self.btn_tab_activity.setCursor(Qt.PointingHandCursor)
        self.btn_tab_activity.clicked.connect(lambda: self._switch_view(1))
        switcher_layout.addWidget(self.btn_tab_activity)

        header.addWidget(switcher_frame)
        header.addStretch()

        # Live indicator
        live_container = QHBoxLayout()
        live_container.setSpacing(6)
        dot = PulsingDot(COLORS["accent_secondary"])
        live_container.addWidget(dot)
        live_label = QLabel("LIVE PC SYNC")
        live_label.setStyleSheet(
            f"color: {COLORS['accent_secondary']}; font-size: 11px; "
            f"font-weight: bold; letter-spacing: 1.5px;"
        )
        live_container.addWidget(live_label)

        header.addLayout(live_container)
        main_layout.addLayout(header)

        # ─── Stacked Widget (Wellbeing vs System Activity) ───────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Page 0: Digital Wellbeing
        self.wellbeing_page = DigitalWellbeingPage()
        self.stack.addWidget(self.wellbeing_page)

        # Page 1: Original System Activity Dashboard Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        # ─── Stats Cards ────────────────────────────────────────
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.stat_total = StatCard(
            "📊", "Total Events (24h)", "0",
            COLORS["accent_primary"]
        )
        self.stat_processes = StatCard(
            "⚡", "Active Processes", "0",
            COLORS["accent_secondary"]
        )
        self.stat_files = StatCard(
            "📁", "File Changes", "0",
            COLORS["accent_blue"]
        )
        self.stat_errors = StatCard(
            "⚠️", "Errors & Crashes", "0",
            COLORS["severity_error"]
        )

        stats_grid.addWidget(self.stat_total, 0, 0)
        stats_grid.addWidget(self.stat_processes, 0, 1)
        stats_grid.addWidget(self.stat_files, 0, 2)
        stats_grid.addWidget(self.stat_errors, 0, 3)

        scroll_layout.addLayout(stats_grid)

        # ─── Activity Chart ─────────────────────────────────────
        chart_frame = QFrame()
        chart_frame.setProperty("class", "card")
        chart_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        chart_layout.setSpacing(12)

        chart_title = QLabel("📈  Activity (Last 24 Hours)")
        chart_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; border: none;"
        )
        chart_layout.addWidget(chart_title)

        self.activity_chart = ActivityChart()
        chart_layout.addWidget(self.activity_chart)

        scroll_layout.addWidget(chart_frame)

        # ─── Category Breakdown + Recent Events ──────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # Category breakdown
        cat_frame = QFrame()
        cat_frame.setProperty("class", "card")
        cat_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )
        cat_frame.setMinimumWidth(280)
        cat_frame.setMaximumWidth(340)

        cat_layout = QVBoxLayout(cat_frame)
        cat_layout.setContentsMargins(20, 20, 20, 20)
        cat_layout.setSpacing(12)

        cat_title = QLabel("📋  Categories")
        cat_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; border: none;"
        )
        cat_layout.addWidget(cat_title)

        self.category_container = QVBoxLayout()
        self.category_container.setSpacing(8)
        cat_layout.addLayout(self.category_container)
        cat_layout.addStretch()

        bottom_row.addWidget(cat_frame)

        # Recent events
        recent_frame = QFrame()
        recent_frame.setProperty("class", "card")
        recent_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )

        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        recent_layout.setSpacing(12)

        recent_title = QLabel("🕐  Recent Events")
        recent_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; border: none;"
        )
        recent_layout.addWidget(recent_title)

        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recent_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self.recent_container_widget = QWidget()
        self.recent_container = QVBoxLayout(self.recent_container_widget)
        self.recent_container.setContentsMargins(0, 0, 0, 0)
        self.recent_container.setSpacing(8)
        self.recent_container.addStretch()
        self.recent_scroll.setWidget(self.recent_container_widget)

        recent_layout.addWidget(self.recent_scroll)
        bottom_row.addWidget(recent_frame, 1)

        scroll_layout.addLayout(bottom_row)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        self.stack.addWidget(scroll)
        main_layout.addWidget(self.stack, 1)

        # Default to Digital Wellbeing view
        self._switch_view(0)

    def _switch_view(self, idx: int):
        """Switch between Digital Wellbeing and System Activity views."""
        self._current_view_idx = idx
        self.stack.setCurrentIndex(idx)

        active_btn_style = (
            f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 6px 16px; font-weight: 700; font-size: 13px; }}"
        )
        inactive_btn_style = (
            f"QPushButton {{ background-color: transparent; color: {COLORS['text_secondary']}; "
            f"border: none; border-radius: 6px; padding: 6px 16px; font-weight: 500; font-size: 13px; }} "
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; background-color: {COLORS['bg_lighter']}; }}"
        )

        if idx == 0:
            self.btn_tab_wellbeing.setStyleSheet(active_btn_style)
            self.btn_tab_activity.setStyleSheet(inactive_btn_style)
            self.wellbeing_page.refresh_data()
        else:
            self.btn_tab_wellbeing.setStyleSheet(inactive_btn_style)
            self.btn_tab_activity.setStyleSheet(active_btn_style)

    def on_active_tick(self, tick_data: dict):
        """Forward real-time tick from ScreenTimeMonitor to wellbeing view."""
        self.wellbeing_page.on_active_tick(tick_data)

    @Slot()
    def refresh_data(self):
        """Refresh dashboard data from the database."""
        try:
            self.wellbeing_page.refresh_data()
        except Exception:
            pass

        try:
            stats = self.db.get_stats(hours=24)

            # Update stat cards
            self.stat_total.set_value(stats.get("total_events", 0))
            self.stat_errors.set_value(stats.get("error_count", 0))

            # Category counts
            by_cat = stats.get("by_category", {})
            self.stat_files.set_value(by_cat.get("FileSystem", 0))
            self.stat_processes.set_value(by_cat.get("Application", 0))

            # Update activity chart
            by_hour = stats.get("by_hour", {})
            self.activity_chart.set_data(by_hour)

            # Update category breakdown
            self._update_categories(by_cat)

            # Update recent events
            self._update_recent_events()

        except Exception as e:
            pass  # Silently handle refresh errors

    def _update_categories(self, by_category):
        """Update the category breakdown section."""
        # Clear existing
        while self.category_container.count():
            item = self.category_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat_colors = {
            "Application": COLORS["cat_application"],
            "FileSystem": COLORS["cat_filesystem"],
            "System": COLORS["cat_system"],
            "Crash": COLORS["cat_crash"],
        }

        total = sum(by_category.values()) or 1

        for cat, count in sorted(
            by_category.items(), key=lambda x: x[1], reverse=True
        ):
            color = cat_colors.get(cat, COLORS["text_muted"])
            pct = int(count / total * 100)

            row = QFrame()
            row.setStyleSheet("border: none; background: transparent;")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            # Label row
            label_row = QHBoxLayout()
            name_label = QLabel(f"● {cat}")
            name_label.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: 500; border: none;"
            )
            label_row.addWidget(name_label)
            label_row.addStretch()

            count_label = QLabel(f"{count}  ({pct}%)")
            count_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 12px; border: none;"
            )
            label_row.addWidget(count_label)
            row_layout.addLayout(label_row)

            # Progress bar
            bar_bg = QFrame()
            bar_bg.setFixedHeight(6)
            bar_bg.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; "
                f"border-radius: 3px; border: none;"
            )
            bar_bg_layout = QHBoxLayout(bar_bg)
            bar_bg_layout.setContentsMargins(0, 0, 0, 0)
            bar_bg_layout.setSpacing(0)

            bar_fill = QFrame()
            bar_fill.setFixedHeight(6)
            bar_fill.setFixedWidth(max(int(pct * 2.5), 3))
            bar_fill.setStyleSheet(
                f"background-color: {color}; border-radius: 3px; border: none;"
            )
            bar_bg_layout.addWidget(bar_fill)
            bar_bg_layout.addStretch()

            row_layout.addWidget(bar_bg)
            self.category_container.addWidget(row)

    def _update_recent_events(self):
        """Update the recent events list."""
        # Clear existing event cards
        while self.recent_container.count() > 1:  # Keep the stretch
            item = self.recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        events = self.db.get_events(limit=15)

        for event in events:
            card = EventCard(event)
            self.recent_container.insertWidget(
                self.recent_container.count() - 1, card
            )

    def add_live_event(self, event_data):
        """Add a new event to the recent list in real-time."""
        # Just refresh — simpler and avoids duplicate tracking
        self.refresh_data()
