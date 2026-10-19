"""
LOG NEST - Digital Wellbeing Widgets
Android-inspired Digital Wellbeing UI components:
- Circular screen time donut ring chart
- Live active foreground application stopwatch card
- App usage breakdown rows with launch counts and limit progress
- Daily app limit manager dialog
- Focus mode & bedtime schedule controls
- Hourly screen time bar chart
"""

import math
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QDialog, QSpinBox,
    QCheckBox, QDialogButtonBox, QSizePolicy, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QRectF, QTimer, QSize
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPainterPath
)

from src.ui.theme import COLORS, category_color
from src.utils.helpers import format_screen_time, format_duration


WELLBEING_PALETTE = [
    "#6C63FF",  # Electric Violet / Primary
    "#00D4AA",  # Mint / Teal
    "#FF6B8A",  # Neon Coral
    "#4FC3F7",  # Bright Cyan
    "#FFB74D",  # Warm Amber
    "#B388FF",  # Soft Lavender
    "#00E676",  # Lime Green
    "#FF4081",  # Deep Pink
    "#80D8FF",  # Sky
    "#FFD54F",  # Yellow
]


class WellbeingRingChart(QWidget):
    """
    Android Digital Wellbeing circular donut chart.
    Displays total screen time today in center and app segments around the ring.
    """

    app_clicked = Signal(str)  # Emits app_id when segment clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._total_seconds: float = 0.0
        self._apps_data: List[Dict[str, Any]] = []
        self._center_title: str = "0 min"
        self._center_subtitle: str = "Screen time today"
        self._sync_status: str = "LIVE SYNC"

    def set_data(self, total_seconds: float, apps: List[Dict[str, Any]], sync_time: str = ""):
        """Update chart with screen time totals and top applications."""
        self._total_seconds = max(total_seconds, 0.0)
        self._apps_data = apps or []
        self._center_title = format_screen_time(self._total_seconds)
        if sync_time:
            self._sync_status = f"SYNCED {sync_time}"
        self.update()

    def paintEvent(self, event):
        """Paint circular donut ring with smooth antialiasing and app segments."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 24
        cx = w / 2.0
        cy = h / 2.0
        radius = size / 2.0
        ring_thickness = max(min(radius * 0.22, 32.0), 18.0)

        rect = QRectF(cx - radius + ring_thickness / 2.0,
                      cy - radius + ring_thickness / 2.0,
                      size - ring_thickness,
                      size - ring_thickness)

        # 1. Background ring track
        track_color = QColor(COLORS["bg_lighter"])
        track_color.setAlpha(120)
        track_pen = QPen(track_color, ring_thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # 2. Draw colored app segments
        if self._total_seconds > 0 and self._apps_data:
            start_angle = 90.0 * 16.0  # Top center (12 o'clock), 16ths of a degree
            gap_angle = 2.0 * 16.0     # Small aesthetic separation between segments

            # Limit to top 7 apps, remainder into 'Other'
            top_apps = self._apps_data[:7]
            sum_top = sum(a.get("duration_seconds", 0) for a in top_apps)
            other_sec = max(self._total_seconds - sum_top, 0.0)

            segments = list(top_apps)
            if other_sec > 30:
                segments.append({
                    "app_id": "other",
                    "app_name": "Other Apps",
                    "duration_seconds": other_sec,
                })

            for i, seg in enumerate(segments):
                sec = seg.get("duration_seconds", 0)
                if sec <= 0:
                    continue

                fraction = sec / self._total_seconds
                span_angle = -(fraction * 360.0 * 16.0)

                # Avoid gap if only 1 segment
                actual_span = span_angle
                if len(segments) > 1 and abs(actual_span) > gap_angle:
                    actual_span = span_angle + (gap_angle if span_angle < 0 else -gap_angle)

                color_hex = WELLBEING_PALETTE[i % len(WELLBEING_PALETTE)]
                seg_pen = QPen(QColor(color_hex), ring_thickness, Qt.SolidLine, Qt.RoundCap)
                painter.setPen(seg_pen)
                painter.drawArc(rect, int(start_angle), int(actual_span))

                start_angle += span_angle

        # 3. Center Information text
        # Sync Status badge at top of inner circle
        painter.setPen(QColor(COLORS["accent_secondary"]))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        status_rect = QRectF(cx - 100, cy - radius * 0.45, 200, 20)
        painter.drawText(status_rect, Qt.AlignCenter, f"● {self._sync_status}")

        # Big Bold Screen Time
        painter.setPen(QColor(COLORS["text_primary"]))
        time_font_size = max(int(radius * 0.23), 16)
        painter.setFont(QFont("Segoe UI", time_font_size, QFont.Bold))
        time_rect = QRectF(cx - radius * 0.8, cy - radius * 0.22, radius * 1.6, radius * 0.5)
        painter.drawText(time_rect, Qt.AlignCenter, self._center_title)

        # Subtitle "Screen time today"
        painter.setPen(QColor(COLORS["text_secondary"]))
        sub_font_size = max(int(radius * 0.11), 10)
        painter.setFont(QFont("Segoe UI", sub_font_size, QFont.Medium))
        sub_rect = QRectF(cx - 100, cy + radius * 0.22, 200, 24)
        painter.drawText(sub_rect, Qt.AlignCenter, self._center_subtitle)

        painter.end()


class LiveActiveAppCard(QFrame):
    """Card displaying currently active foreground application and live focus stopwatch."""

    set_limit_requested = Signal(str, str)  # app_id, app_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {COLORS['bg_card']}, stop:1 {COLORS['bg_medium']}); "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 14px; }}"
        )
        self._current_app_id = ""
        self._current_app_name = "Desktop"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header with pulse
        header = QHBoxLayout()
        header.setSpacing(8)

        self.pulse_label = QLabel("● REAL-TIME FOCUS")
        self.pulse_label.setStyleSheet(
            f"color: {COLORS['accent_secondary']}; font-size: 11px; "
            f"font-weight: 800; letter-spacing: 1.5px; border: none; background: transparent;"
        )
        header.addWidget(self.pulse_label)
        header.addStretch()

        self.btn_limit = QPushButton("⏱️ Set Limit")
        self.btn_limit.setCursor(Qt.PointingHandCursor)
        self.btn_limit.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_lighter']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600; }} "
            f"QPushButton:hover {{ background-color: {COLORS['accent_primary']}; border-color: {COLORS['accent_primary']}; }}"
        )
        self.btn_limit.clicked.connect(self._on_limit_click)
        header.addWidget(self.btn_limit)
        layout.addLayout(header)

        # Main App info row
        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        self.icon_badge = QLabel("🖥️")
        self.icon_badge.setFixedSize(48, 48)
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 12px; font-size: 22px;"
        )
        content_row.addWidget(self.icon_badge)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)

        self.app_title = QLabel("Desktop / Explorer")
        self.app_title.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        info_vbox.addWidget(self.app_title)

        self.category_label = QLabel("System")
        self.category_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        info_vbox.addWidget(self.category_label)
        content_row.addLayout(info_vbox, 1)

        # Live Focus Timer
        timer_vbox = QVBoxLayout()
        timer_vbox.setSpacing(2)
        timer_vbox.setAlignment(Qt.AlignRight)

        self.stopwatch_label = QLabel("00:00:00")
        self.stopwatch_label.setStyleSheet(
            f"font-size: 20px; font-weight: 800; font-family: 'Consolas', 'Courier New', monospace; "
            f"color: {COLORS['accent_secondary']}; border: none; background: transparent;"
        )
        timer_vbox.addWidget(self.stopwatch_label, 0, Qt.AlignRight)

        self.session_sub = QLabel("Current Session")
        self.session_sub.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        timer_vbox.addWidget(self.session_sub, 0, Qt.AlignRight)
        content_row.addLayout(timer_vbox)

        layout.addLayout(content_row)

        # Cumulative today stats
        self.cumul_label = QLabel("Today's cumulative usage: 0 min")
        self.cumul_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_secondary']}; border-top: 1px solid {COLORS['border']}; "
            f"padding-top: 8px; margin-top: 4px; background: transparent;"
        )
        layout.addWidget(self.cumul_label)

    def update_tick(self, tick_data: Dict[str, Any]):
        """Update live foreground app details from ScreenTimeMonitor tick."""
        app_id = tick_data.get("app_id", "")
        app_name = tick_data.get("app_name", "Unknown")
        category = tick_data.get("category", "General")
        is_idle = tick_data.get("is_idle", False)
        session_sec = int(tick_data.get("session_seconds", 0))
        today_sec = tick_data.get("app_today_seconds", 0)

        self._current_app_id = app_id
        self._current_app_name = app_name

        if is_idle:
            self.pulse_label.setText("⏸ SCREEN PAUSED (USER IDLE)")
            self.pulse_label.setStyleSheet(
                f"color: {COLORS['severity_warning']}; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; border: none; background: transparent;"
            )
            self.stopwatch_label.setStyleSheet(
                f"font-size: 20px; font-weight: 800; font-family: 'Consolas', monospace; "
                f"color: {COLORS['severity_warning']}; border: none; background: transparent;"
            )
            self.app_title.setText("Idle / Away")
            self.category_label.setText("Screen time paused after 2 min of inactivity")
            self.icon_badge.setText("💤")
            self.cumul_label.setText("Activity resumes automatically when you move the mouse or type.")
            self.btn_limit.setVisible(False)
        else:
            self.pulse_label.setText("● ACTIVE WINDOW (LIVE PC SYNC)")
            self.pulse_label.setStyleSheet(
                f"color: {COLORS['accent_secondary']}; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; border: none; background: transparent;"
            )
            self.stopwatch_label.setStyleSheet(
                f"font-size: 20px; font-weight: 800; font-family: 'Consolas', monospace; "
                f"color: {COLORS['accent_secondary']}; border: none; background: transparent;"
            )
            self.app_title.setText(app_name)
            self.category_label.setText(category)
            self.btn_limit.setVisible(bool(app_id and app_id != "idle"))

            # Icon choice
            cat_icons = {
                "Browser": "🌐",
                "Developer Tool": "💻",
                "Productivity": "📝",
                "Communication": "💬",
                "Media": "🎵",
                "Gaming": "🎮",
                "Creative": "🎨",
                "System": "⚙️",
            }
            self.icon_badge.setText(cat_icons.get(category, "📱"))

            # Stopwatch format HH:MM:SS
            hrs = session_sec // 3600
            mins = (session_sec % 3600) // 60
            secs = session_sec % 60
            self.stopwatch_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

            cumul_text = format_screen_time(today_sec, detailed=True)
            self.cumul_label.setText(f"Today's cumulative usage: {cumul_text}")

    def _on_limit_click(self):
        if self._current_app_id:
            self.set_limit_requested.emit(self._current_app_id, self._current_app_name)


class AppUsageRowWidget(QFrame):
    """A row representing an app's usage today, with bar, percentage, opens, and limit badge."""

    set_limit_clicked = Signal(str, str)  # app_id, app_name

    def __init__(self, app_data: Dict[str, Any], color_hex: str, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.color_hex = color_hex
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 10px; padding: 4px; }} "
            f"QFrame:hover {{ border-color: {color_hex}; background-color: {COLORS['bg_hover']}; }}"
        )
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # 1. Color tag / Icon
        color_dot = QFrame()
        color_dot.setFixedSize(12, 12)
        color_dot.setStyleSheet(f"background-color: {self.color_hex}; border-radius: 6px; border: none;")
        layout.addWidget(color_dot)

        # 2. App name + Category + Opens
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        app_name = self.app_data.get("app_name", "Application")
        title_label = QLabel(app_name)
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        info_col.addWidget(title_label)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(8)

        cat_badge = QLabel(self.app_data.get("category", "General"))
        cat_badge.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {self.color_hex}; "
            f"background-color: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 4px; padding: 1px 6px;"
        )
        sub_row.addWidget(cat_badge)

        launches = self.app_data.get("launches", 0)
        launches_text = f"Opened {launches} time{'s' if launches != 1 else ''}"
        launches_label = QLabel(launches_text)
        launches_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        sub_row.addWidget(launches_label)
        sub_row.addStretch()

        info_col.addLayout(sub_row)
        layout.addLayout(info_col, 2)

        # 3. Usage bar + percentage
        bar_col = QVBoxLayout()
        bar_col.setSpacing(4)

        pct = self.app_data.get("percentage", 0.0)
        dur_sec = self.app_data.get("duration_seconds", 0.0)
        dur_text = format_screen_time(dur_sec)

        dur_label = QLabel(f"{dur_text}  ({pct:.1f}%)")
        dur_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        dur_label.setAlignment(Qt.AlignRight)
        bar_col.addWidget(dur_label)

        # Horizontal progress bar
        bar_bg = QFrame()
        bar_bg.setFixedHeight(6)
        bar_bg.setStyleSheet(f"background-color: {COLORS['bg_lighter']}; border-radius: 3px; border: none;")
        bar_layout = QHBoxLayout(bar_bg)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        bar_fill = QFrame()
        bar_fill.setFixedHeight(6)
        bar_fill_width = max(int(pct * 2.2), 4)
        bar_fill.setFixedWidth(min(bar_fill_width, 220))
        bar_fill.setStyleSheet(f"background-color: {self.color_hex}; border-radius: 3px; border: none;")
        bar_layout.addWidget(bar_fill)
        bar_layout.addStretch()

        bar_col.addWidget(bar_bg)
        layout.addLayout(bar_col, 2)

        # 4. Limit Badge / Action
        limit_mins = self.app_data.get("daily_limit_minutes")
        limit_enabled = self.app_data.get("limit_enabled")

        btn_limit = QPushButton()
        btn_limit.setCursor(Qt.PointingHandCursor)

        if limit_mins and limit_enabled:
            limit_sec = limit_mins * 60.0
            if dur_sec >= limit_sec:
                btn_limit.setText(f"⚠️ Limit Reached ({limit_mins}m)")
                btn_limit.setStyleSheet(
                    f"QPushButton {{ background-color: #5C1D24; color: {COLORS['severity_error']}; "
                    f"border: 1px solid {COLORS['severity_error']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 700; }} "
                    f"QPushButton:hover {{ background-color: {COLORS['severity_error']}; color: white; }}"
                )
            else:
                rem_mins = int((limit_sec - dur_sec) // 60)
                btn_limit.setText(f"⏱️ {rem_mins}m left of {limit_mins}m")
                btn_limit.setStyleSheet(
                    f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['accent_secondary']}; "
                    f"border: 1px solid {COLORS['border_light']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600; }} "
                    f"QPushButton:hover {{ border-color: {COLORS['accent_secondary']}; }}"
                )
        else:
            btn_limit.setText("⏱️ Set Limit")
            btn_limit.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {COLORS['text_muted']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px 8px; font-size: 11px; }} "
                f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['border_light']}; }}"
            )

        btn_limit.clicked.connect(lambda: self.set_limit_clicked.emit(
            self.app_data.get("app_id", ""), self.app_data.get("app_name", "")
        ))
        layout.addWidget(btn_limit)


class DailyLimitDialog(QDialog):
    """Dialog allowing user to set a daily screen time limit for an app."""

    def __init__(self, app_id: str, app_name: str, current_limit_mins: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.app_name = app_name
        self.setWindowTitle(f"Daily Limit — {app_name}")
        self.setFixedSize(380, 280)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']}; color: {COLORS['text_primary']};")

        self.limit_minutes: int = current_limit_mins or 60
        self.remove_requested: bool = False
        self._setup_ui(current_limit_mins)

    def _setup_ui(self, current_limit_mins):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(f"Set Daily Screen Time Limit")
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {COLORS['text_primary']};")
        layout.addWidget(title)

        desc = QLabel(f"LOG NEST will alert you when you have spent your daily limit on <b>{self.app_name}</b> today.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        layout.addWidget(desc)

        # Quick preset buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for mins, label in [(15, "15m"), (30, "30m"), (45, "45m"), (60, "1 hr"), (120, "2 hr")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_primary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; font-weight: 600; }} "
                f"QPushButton:hover {{ border-color: {COLORS['accent_primary']}; }}"
            )
            btn.clicked.connect(lambda ch, m=mins: self.spin_mins.setValue(m))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        # Custom spinbox
        spin_row = QHBoxLayout()
        spin_label = QLabel("Daily limit (minutes):")
        spin_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 500;")
        spin_row.addWidget(spin_label)

        self.spin_mins = QSpinBox()
        self.spin_mins.setRange(1, 1440)
        self.spin_mins.setValue(current_limit_mins or 60)
        self.spin_mins.setStyleSheet(
            f"QSpinBox {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 6px; padding: 6px; font-size: 14px; }}"
        )
        spin_row.addWidget(self.spin_mins)
        layout.addLayout(spin_row)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()
        if current_limit_mins:
            btn_remove = QPushButton("Remove Limit")
            btn_remove.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {COLORS['severity_error']}; "
                f"border: 1px solid {COLORS['severity_error']}; border-radius: 6px; padding: 8px 14px; font-weight: 600; }} "
                f"QPushButton:hover {{ background-color: {COLORS['severity_error']}; color: white; }}"
            )
            btn_remove.clicked.connect(self._on_remove)
            btn_layout.addWidget(btn_remove)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px 14px; }} "
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; }}"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Limit")
        btn_save.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 8px 18px; font-weight: 700; }} "
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_save(self):
        self.limit_minutes = self.spin_mins.value()
        self.remove_requested = False
        self.accept()

    def _on_remove(self):
        self.remove_requested = True
        self.accept()


class FocusModeWidget(QFrame):
    """Widget for Focus Mode (Pomodoro/Distraction-Free session) and Bedtime Mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 12px; padding: 6px; }}"
        )
        self._focus_remaining_seconds: int = 25 * 60
        self._focus_active: bool = False
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._on_focus_tick)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("🎯  Focus Mode & Bedtime")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']}; border: none;")
        header.addWidget(title)
        header.addStretch()

        self.bedtime_badge = QLabel("🌙 Bedtime: 11 PM – 7 AM")
        self.bedtime_badge.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {COLORS['text_secondary']}; "
            f"background-color: {COLORS['bg_medium']}; border-radius: 4px; padding: 2px 6px; border: none;"
        )
        header.addWidget(self.bedtime_badge)
        layout.addLayout(header)

        # Timer Display
        timer_box = QHBoxLayout()
        timer_box.setSpacing(12)

        self.timer_label = QLabel("25:00")
        self.timer_label.setStyleSheet(
            f"font-size: 26px; font-weight: 800; font-family: 'Consolas', monospace; "
            f"color: {COLORS['accent_primary']}; border: none; background: transparent;"
        )
        timer_box.addWidget(self.timer_label)

        self.btn_toggle = QPushButton("Start Focus (25m)")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 8px 16px; font-weight: 700; font-size: 12px; }} "
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        self.btn_toggle.clicked.connect(self._toggle_focus)
        timer_box.addWidget(self.btn_toggle)

        btn_reset = QPushButton("Reset")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px 12px; font-size: 12px; }} "
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; }}"
        )
        btn_reset.clicked.connect(self._reset_focus)
        timer_box.addWidget(btn_reset)

        timer_box.addStretch()
        layout.addLayout(timer_box)

        # Quick preset buttons (15m, 25m, 45m, 60m)
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        preset_lbl = QLabel("Presets:")
        preset_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; border: none;")
        presets_layout.addWidget(preset_lbl)

        for mins in [15, 25, 45, 60]:
            p_btn = QPushButton(f"{mins}m")
            p_btn.setCursor(Qt.PointingHandCursor)
            p_btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 8px; font-size: 11px; }} "
                f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['accent_primary']}; }}"
            )
            p_btn.clicked.connect(lambda ch, m=mins: self._set_focus_duration(m))
            presets_layout.addWidget(p_btn)

        presets_layout.addStretch()
        layout.addLayout(presets_layout)

    def _toggle_focus(self):
        if not self._focus_active:
            self._focus_active = True
            self._focus_timer.start(1000)
            self.btn_toggle.setText("Pause Focus")
            self.btn_toggle.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['severity_warning']}; color: #0A0E17; "
                f"border: none; border-radius: 6px; padding: 8px 16px; font-weight: 700; font-size: 12px; }}"
            )
        else:
            self._focus_active = False
            self._focus_timer.stop()
            self.btn_toggle.setText("Resume Focus")
            self.btn_toggle.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
                f"border: none; border-radius: 6px; padding: 8px 16px; font-weight: 700; font-size: 12px; }}"
            )

    def _reset_focus(self):
        self._focus_active = False
        self._focus_timer.stop()
        self._focus_remaining_seconds = 25 * 60
        self._update_display()
        self.btn_toggle.setText("Start Focus (25m)")
        self.btn_toggle.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 8px 16px; font-weight: 700; font-size: 12px; }}"
        )

    def _set_focus_duration(self, minutes: int):
        self._focus_active = False
        self._focus_timer.stop()
        self._focus_remaining_seconds = minutes * 60
        self._update_display()
        self.btn_toggle.setText(f"Start Focus ({minutes}m)")

    def _on_focus_tick(self):
        if self._focus_remaining_seconds > 0:
            self._focus_remaining_seconds -= 1
            self._update_display()
        else:
            self._focus_active = False
            self._focus_timer.stop()
            self.btn_toggle.setText("Session Complete! 🎉")

    def _update_display(self):
        mins = self._focus_remaining_seconds // 60
        secs = self._focus_remaining_seconds % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")


class HourlyScreenTimeChart(QWidget):
    """Bar chart displaying today's screen time per hour (0..23)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMinimumWidth(280)
        self._data: Dict[int, float] = {h: 0.0 for h in range(24)}
        self._max_seconds: float = 3600.0

    def set_data(self, hourly_map: Dict[int, float]):
        """Set screen time data per hour in seconds."""
        self._data = hourly_map or {h: 0.0 for h in range(24)}
        max_val = max(self._data.values()) if self._data else 0.0
        self._max_seconds = max(max_val, 1800.0)  # at least 30 mins scale
        self.update()

    def paintEvent(self, event):
        """Paint clean hourly screen time bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_bottom = 24
        padding_top = 10
        padding_sides = 12

        chart_w = w - 2 * padding_sides
        chart_h = h - padding_bottom - padding_top

        current_hour = datetime.now().hour
        bar_gap = 2
        bar_w = max((chart_w / 24.0) - bar_gap, 3.0)

        for hour in range(24):
            sec = self._data.get(hour, 0.0)
            bar_height = max((sec / self._max_seconds) * chart_h, 3.0) if self._max_seconds > 0 else 3.0
            x = padding_sides + hour * (bar_w + bar_gap)
            y = padding_top + chart_h - bar_height

            is_now = (hour == current_hour)
            bar_color = QColor(COLORS["accent_secondary"] if is_now else COLORS["accent_primary"])
            if sec == 0:
                bar_color.setAlpha(60)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_height), 2, 2)

            # Hour labels (every 4 hours: 0, 4, 8, 12, 16, 20)
            if hour % 4 == 0 or hour == 23:
                painter.setPen(QColor(COLORS["text_muted"]))
                painter.setFont(QFont("Segoe UI", 8))
                lbl = f"{hour:02d}"
                painter.drawText(QRectF(x - 6, h - padding_bottom + 4, bar_w + 12, 16), Qt.AlignCenter, lbl)

        painter.end()
