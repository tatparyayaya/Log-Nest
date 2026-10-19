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
        from src.ui.reference_widgets import ForestHeader, MetricCard, surface, heading, disclosure
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        header_frame = ForestHeader()
        header_frame.setFixedHeight(138)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(34, 24, 28, 24)
        title_box = QVBoxLayout()
        title_box.addWidget(heading("Digital Wellbeing", 30))
        self.sync_badge = QLabel("●  Real-time PC Sync")
        self.sync_badge.setStyleSheet("color:#00ce8c;font-size:17px;background:transparent;border:none")
        title_box.addWidget(self.sync_badge)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        clock_box = QVBoxLayout()
        self.clock_label = heading(datetime.now().strftime("%I:%M:%S %p"), 28)
        self.date_label = QLabel(datetime.now().strftime("%A, %B %d, %Y"))
        self.date_label.setStyleSheet("color:#91aaca;font-size:15px;background:transparent;border:none")
        clock_box.addWidget(self.clock_label, 0, Qt.AlignRight)
        clock_box.addWidget(self.date_label, 0, Qt.AlignRight)
        header_layout.addLayout(clock_box)
        for attr, text, callback in [("btn_prev_day", "‹", self._prev_day), ("btn_today", "Today", self._go_today), ("btn_next_day", "›", self._next_day)]:
            btn = QPushButton(text)
            btn.setFixedSize(94 if text == "Today" else 48, 48)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:" + ("#155ee4" if text == "Today" else "#192535") + ";color:white;border:1px solid #233247;border-radius:17px;font-size:18px} QPushButton:hover{border-color:#408bff}")
            btn.clicked.connect(callback)
            setattr(self, attr, btn)
            header_layout.addWidget(btn)
        main_layout.addWidget(header_frame)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent} QScrollArea>QWidget>QWidget{background:transparent}")
        content = QWidget()
        column = QVBoxLayout(content)
        column.setContentsMargins(0,0,0,0)
        column.setSpacing(16)
        stats = QHBoxLayout()
        stats.setSpacing(16)
        for attr, icon, title, color in [("stat_screen_time","monitor","Screen Time Today","#00baff"),("stat_launches","grid","App Launches Today","#00ce8c"),("stat_active_apps","layers","Apps Used Today","#af55ff"),("stat_limits","warning","Limits Reached","#ffbf21")]:
            card = MetricCard(icon, title, color)
            setattr(self, attr, card)
            stats.addWidget(card, 1)
        column.addLayout(stats)
        hero = QHBoxLayout()
        hero.setSpacing(16)
        donut = surface()
        dl = QVBoxLayout(donut)
        dl.setContentsMargins(28,24,28,24)
        title_row = QHBoxLayout()
        title_row.addWidget(heading("Screen Time Distribution",24))
        title_row.addStretch()
        more = QPushButton("••• More")
        more.setFixedSize(82,42)
        more.setStyleSheet("background:#1a2738;border:1px solid #26364c;border-radius:15px;color:white")
        title_row.addWidget(more)
        dl.addLayout(title_row)
        self.ring_chart = WellbeingRingChart()
        dl.addWidget(self.ring_chart,1,Qt.AlignCenter)
        self.legend_container = QHBoxLayout()
        self.legend_container.setSpacing(6)
        dl.addLayout(self.legend_container)
        hero.addWidget(donut, 8)
        from src.ui.active_windows import ActiveWindowsCarousel
        self.live_card = ActiveWindowsCarousel()
        self.live_card.set_limit_requested.connect(self._open_limit_dialog)
        hero.addWidget(self.live_card, 5)
        column.addLayout(hero,1)
        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        apps_frame = surface()
        al = QVBoxLayout(apps_frame)
        al.setContentsMargins(28,18,28,18)
        self.app_count_label = QLabel("0 apps tracked")
        self.app_count_label.setStyleSheet("color:#91aaca;font-size:15px;border:none;background:transparent")
        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setMinimumHeight(280)
        self.apps_scroll.setStyleSheet("border:none;background:transparent")
        self.apps_container_widget = QWidget()
        self.apps_container = QVBoxLayout(self.apps_container_widget)
        self.apps_container.addStretch()
        self.apps_scroll.setWidget(self.apps_container_widget)
        apps_toggle = disclosure(al,"Application Usage",self.apps_scroll,self.app_count_label)
        more.clicked.connect(apps_toggle.click)
        bottom.addWidget(apps_frame,5)
        hourly_frame = surface()
        hl = QVBoxLayout(hourly_frame)
        hl.setContentsMargins(28,18,28,18)
        details = QWidget()
        detail_layout = QVBoxLayout(details)
        self.hourly_chart = HourlyScreenTimeChart()
        detail_layout.addWidget(self.hourly_chart)
        self.focus_widget = FocusModeWidget()
        detail_layout.addWidget(self.focus_widget)
        disclosure(hl,"Hourly Activity (Today)",details)
        bottom.addWidget(hourly_frame,4)
        column.addLayout(bottom)
        scroll.setWidget(content)
        main_layout.addWidget(scroll,1)

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
        if getattr(self, "_rendered_legend", None) == top_apps:
            return
        self._rendered_legend = [dict(app) for app in top_apps]
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
                f"background-color: {COLORS['bg_medium']}; border-radius: 20px; padding: 2px 6px; border: none;"
            )
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(10, 10, 10, 10)
            pill_layout.setSpacing(4)

            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
            pill_layout.addWidget(dot)

            lbl = QLabel(f"{name}: {dur}")
            lbl.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']}; border: none;")
            pill_layout.addWidget(lbl)

            self.legend_container.addWidget(pill)

        self.legend_container.addStretch()

    def _update_app_rows(self, apps: List[Dict[str, Any]]):
        """Populate the app usage list."""
        if getattr(self, "_rendered_apps", None) == apps:
            return
        self._rendered_apps = [dict(app) for app in apps]
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
        self.date_label.setText(datetime.now().strftime("%A, %B %d, %Y"))
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
