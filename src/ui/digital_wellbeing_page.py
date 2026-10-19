"""
LOG NEST - Digital Wellbeing Page (Professional Windows Desktop Design)
Clean dark graphite layout with muted blue accents, balanced spacing,
compact cards, and zero overflow.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Slot

from src.database import DatabaseManager
from src.ui.theme import COLORS
from src.ui.widgets import StatCard
from src.ui.wellbeing_widgets import (
    WellbeingRingChart, LiveActiveAppCard, AppUsageRowWidget,
    DailyLimitDialog, FocusModeWidget, HourlyScreenTimeChart,
    WELLBEING_PALETTE
)
from src.utils.helpers import format_screen_time


class DigitalWellbeingPage(QWidget):
    """Clean Digital Wellbeing view aligned with Windows desktop aesthetics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._is_today = True

        self._setup_ui()

        # Real-time clock timer (1s interval)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._clock_timer.start(1000)

        # Initial load
        QTimer.singleShot(40, self.refresh_data)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # ─── Top Header: PC Clock & Date Navigation ─────────────
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_dark']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 8, 14, 8)
        header_layout.setSpacing(12)

        # Left: Title + Sync status
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)

        page_title = QLabel("Digital Wellbeing")
        page_title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        title_vbox.addWidget(page_title)

        self.sync_badge = QLabel("● Real-time PC Sync")
        self.sync_badge.setStyleSheet(
            f"font-size: 11px; color: {COLORS['accent_secondary']}; border: none; background: transparent;"
        )
        title_vbox.addWidget(self.sync_badge)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        # Center/Right: Live PC Clock Display
        clock_vbox = QVBoxLayout()
        clock_vbox.setSpacing(0)
        clock_vbox.setAlignment(Qt.AlignRight)

        now = datetime.now()
        self.clock_label = QLabel(now.strftime("%I:%M:%S %p"))
        self.clock_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; font-family: 'Segoe UI', monospace; "
            f"color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        clock_vbox.addWidget(self.clock_label, 0, Qt.AlignRight)

        self.date_label = QLabel(now.strftime("%A, %B %d, %Y"))
        self.date_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        clock_vbox.addWidget(self.date_label, 0, Qt.AlignRight)
        header_layout.addLayout(clock_vbox)

        # Date navigation controls: [ ‹ ] [ Today ] [ › ]
        nav_box = QHBoxLayout()
        nav_box.setSpacing(4)

        self.btn_prev_day = QPushButton("‹")
        self.btn_prev_day.setToolTip("Previous Day")
        self.btn_prev_day.setCursor(Qt.PointingHandCursor)
        self.btn_prev_day.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 8px; font-size: 13px; font-weight: bold; }} "
            f"QPushButton:hover {{ border-color: {COLORS['accent_primary']}; }}"
        )
        self.btn_prev_day.clicked.connect(self._prev_day)
        nav_box.addWidget(self.btn_prev_day)

        self.btn_today = QPushButton("Today")
        self.btn_today.setCursor(Qt.PointingHandCursor)
        self.btn_today.setProperty("class", "primary")
        self.btn_today.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
            f"border: 1px solid {COLORS['accent_primary']}; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600; }}"
        )
        self.btn_today.clicked.connect(self._go_today)
        nav_box.addWidget(self.btn_today)

        self.btn_next_day = QPushButton("›")
        self.btn_next_day.setToolTip("Next Day")
        self.btn_next_day.setCursor(Qt.PointingHandCursor)
        self.btn_next_day.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 8px; font-size: 13px; font-weight: bold; }} "
            f"QPushButton:hover {{ border-color: {COLORS['accent_primary']}; }}"
        )
        self.btn_next_day.clicked.connect(self._next_day)
        nav_box.addWidget(self.btn_next_day)

        header_layout.addLayout(nav_box)
        main_layout.addWidget(header_frame)

        # ─── Scroll Area for Content ────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        # ─── 1. Compact Stats Cards Row (4 Columns) ─────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self.stat_screen_time = StatCard("⏱", "Screen Time Today", "0 min", COLORS["accent_primary"])
        self.stat_launches = StatCard("↗", "App Launches Today", "0", COLORS["accent_secondary"])
        self.stat_active_apps = StatCard("▦", "Apps Used Today", "0", COLORS["accent_blue"])
        self.stat_limits = StatCard("⚠", "Limits Reached", "0", COLORS["severity_warning"])

        stats_row.addWidget(self.stat_screen_time)
        stats_row.addWidget(self.stat_launches)
        stats_row.addWidget(self.stat_active_apps)
        stats_row.addWidget(self.stat_limits)
        scroll_layout.addLayout(stats_row)

        # ─── 2. Hero Section: Donut Ring Chart + Live Active Card
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(12)

        # Donut Ring Chart Frame
        donut_frame = QFrame()
        donut_frame.setProperty("class", "card")
        donut_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; }}"
        )
        donut_layout = QVBoxLayout(donut_frame)
        donut_layout.setContentsMargins(14, 12, 14, 12)
        donut_layout.setSpacing(8)

        donut_title = QLabel("Screen Time Distribution")
        donut_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; border: none;")
        donut_layout.addWidget(donut_title)

        donut_center_box = QHBoxLayout()
        self.ring_chart = WellbeingRingChart()
        donut_center_box.addWidget(self.ring_chart)
        donut_layout.addLayout(donut_center_box)

        # Legend pills
        self.legend_container = QHBoxLayout()
        self.legend_container.setSpacing(8)
        donut_layout.addLayout(self.legend_container)

        hero_layout.addWidget(donut_frame, 3)

        # Live Active Card on right
        self.live_card = LiveActiveAppCard()
        self.live_card.set_limit_requested.connect(self._open_limit_dialog)
        hero_layout.addWidget(self.live_card, 4)

        scroll_layout.addLayout(hero_layout)

        # ─── 3. Middle Section: App Breakdown + Hourly / Focus ──
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # Left (58%): App Usage List
        apps_frame = QFrame()
        apps_frame.setProperty("class", "card")
        apps_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; }}"
        )
        apps_layout = QVBoxLayout(apps_frame)
        apps_layout.setContentsMargins(14, 12, 14, 12)
        apps_layout.setSpacing(8)

        apps_header = QHBoxLayout()
        apps_title = QLabel("Application Usage")
        apps_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; border: none;")
        apps_header.addWidget(apps_title)
        apps_header.addStretch()

        self.app_count_label = QLabel("0 apps")
        self.app_count_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; border: none;")
        apps_header.addWidget(self.app_count_label)
        apps_layout.addLayout(apps_header)

        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.apps_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.apps_container_widget = QWidget()
        self.apps_container = QVBoxLayout(self.apps_container_widget)
        self.apps_container.setContentsMargins(0, 0, 0, 0)
        self.apps_container.setSpacing(6)
        self.apps_container.addStretch()
        self.apps_scroll.setWidget(self.apps_container_widget)
        apps_layout.addWidget(self.apps_scroll)

        body_layout.addWidget(apps_frame, 5)

        # Right (42%): Hourly Chart + Focus Mode
        side_vbox = QVBoxLayout()
        side_vbox.setSpacing(12)

        # Hourly Screen Time chart frame
        hourly_frame = QFrame()
        hourly_frame.setProperty("class", "card")
        hourly_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; }}"
        )
        hourly_layout = QVBoxLayout(hourly_frame)
        hourly_layout.setContentsMargins(14, 12, 14, 12)
        hourly_layout.setSpacing(6)

        hourly_title = QLabel("Hourly Activity (Today)")
        hourly_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; border: none;")
        hourly_layout.addWidget(hourly_title)

        self.hourly_chart = HourlyScreenTimeChart()
        hourly_layout.addWidget(self.hourly_chart)
        side_vbox.addWidget(hourly_frame)

        # Focus Mode widget
        self.focus_widget = FocusModeWidget()
        side_vbox.addWidget(self.focus_widget)

        body_layout.addLayout(side_vbox, 4)
        scroll_layout.addLayout(body_layout)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

    @Slot()
    def _on_clock_tick(self):
        """Update PC real-time clock label."""
        now = datetime.now()
        self.clock_label.setText(now.strftime("%I:%M:%S %p"))
        if self._is_today:
            self.date_label.setText(now.strftime("%A, %B %d, %Y"))

    @Slot(dict)
    def on_active_tick(self, tick_data: Dict[str, Any]):
        """Real-time tick from ScreenTimeMonitor."""
        self.live_card.update_tick(tick_data)
        if self._is_today:
            tot_sec = tick_data.get("today_total_seconds", 0)
            self.stat_screen_time.set_value(format_screen_time(tot_sec))

    @Slot()
    def refresh_data(self):
        """Refresh Digital Wellbeing data from SQLite."""
        try:
            summary = self.db.get_daily_screen_time(self._current_date)
            total_sec = summary.get("total_seconds", 0.0)
            total_launches = summary.get("total_launches", 0)
            apps = summary.get("apps", [])

            # Update Stat cards
            self.stat_screen_time.set_value(format_screen_time(total_sec))
            self.stat_launches.set_value(str(total_launches))
            self.stat_active_apps.set_value(str(len(apps)))

            # Count limits reached
            limits_reached = 0
            for app in apps:
                lim = app.get("daily_limit_minutes")
                en = app.get("limit_enabled")
                if lim and en and app.get("duration_seconds", 0) >= lim * 60.0:
                    limits_reached += 1
            self.stat_limits.set_value(str(limits_reached))

            # Update Ring Donut Chart
            now_time = datetime.now().strftime("%I:%M %p")
            self.ring_chart.set_data(total_sec, apps, sync_time=now_time if self._is_today else self._current_date)

            # Update top legend under chart
            self._update_donut_legend(apps[:4], total_sec)

            # Update app breakdown rows
            self._update_app_rows(apps)

            # Update hourly chart
            hourly_map = self.db.get_hourly_screen_time(self._current_date)
            self.hourly_chart.set_data(hourly_map)

        except Exception:
            pass

    def _update_donut_legend(self, top_apps: List[Dict[str, Any]], total_sec: float):
        """Update top app legend pills."""
        while self.legend_container.count():
            item = self.legend_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, app in enumerate(top_apps):
            color = WELLBEING_PALETTE[i % len(WELLBEING_PALETTE)]
            name = app.get("app_name", "App")
            dur = format_screen_time(app.get("duration_seconds", 0))

            pill = QFrame()
            pill.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; border-radius: 4px; padding: 2px 6px; border: none;"
            )
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(4, 2, 4, 2)
            pill_layout.setSpacing(4)

            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
            pill_layout.addWidget(dot)

            lbl = QLabel(f"{name}: {dur}")
            lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['text_secondary']}; border: none;")
            pill_layout.addWidget(lbl)

            self.legend_container.addWidget(pill)

        self.legend_container.addStretch()

    def _update_app_rows(self, apps: List[Dict[str, Any]]):
        """Populate the app usage list."""
        while self.apps_container.count() > 1:
            item = self.apps_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.app_count_label.setText(f"{len(apps)} app{'s' if len(apps) != 1 else ''} tracked")

        if not apps:
            empty_lbl = QLabel("No application usage recorded for this date yet.")
            empty_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.apps_container.insertWidget(0, empty_lbl)
            return

        for i, app in enumerate(apps):
            color = WELLBEING_PALETTE[i % len(WELLBEING_PALETTE)]
            row_widget = AppUsageRowWidget(app, color)
            row_widget.set_limit_clicked.connect(self._open_limit_dialog)
            self.apps_container.insertWidget(self.apps_container.count() - 1, row_widget)

    def _open_limit_dialog(self, app_id: str, app_name: str):
        """Open modal dialog to set or remove a daily limit."""
        limit_entry = self.db.get_app_limit(app_id)
        current_mins = limit_entry.get("daily_limit_minutes") if limit_entry else None

        dlg = DailyLimitDialog(app_id, app_name, current_mins, self)
        if dlg.exec() == DailyLimitDialog.Accepted:
            if dlg.remove_requested:
                self.db.remove_app_limit(app_id)
            else:
                self.db.set_app_limit(app_id, app_name, dlg.limit_minutes, enabled=1)
            self.refresh_data()

    def _go_today(self):
        """Switch view to today."""
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._is_today = True
        self.btn_today.setText("Today")
        self.sync_badge.setText("● Real-time PC Sync")
        self.refresh_data()

    def _prev_day(self):
        """Navigate to previous day."""
        dt = datetime.strptime(self._current_date, "%Y-%m-%d") - timedelta(days=1)
        self._current_date = dt.strftime("%Y-%m-%d")
        self._is_today = (self._current_date == datetime.now().strftime("%Y-%m-%d"))
        self.date_label.setText(dt.strftime("%A, %B %d, %Y"))
        self.btn_today.setText("Today" if not self._is_today else "Today")
        self.sync_badge.setText("● Past History" if not self._is_today else "● Real-time PC Sync")
        self.refresh_data()

    def _next_day(self):
        """Navigate to next day."""
        dt = datetime.strptime(self._current_date, "%Y-%m-%d") + timedelta(days=1)
        self._current_date = dt.strftime("%Y-%m-%d")
        self._is_today = (self._current_date == datetime.now().strftime("%Y-%m-%d"))
        self.date_label.setText(dt.strftime("%A, %B %d, %Y"))
        self.btn_today.setText("Today" if not self._is_today else "Today")
        self.sync_badge.setText("● Viewing Date" if not self._is_today else "● Real-time PC Sync")
        self.refresh_data()
