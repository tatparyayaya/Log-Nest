"""
LOG NEST - Professional Digital Wellbeing Widgets
Clean, realistic Windows desktop components:
- Circular screen time donut ring chart (muted palette, clean typography)
- Compact LiveActiveAppCard (solid background, no flashy effects)
- Compact AppUsageRowWidget with clean progress bars and limit badges
- Refined DailyLimitDialog
- Professional FocusModeWidget & HourlyScreenTimeChart
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDialog, QSpinBox, QSizePolicy, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush
)

from src.ui.theme import COLORS
from src.utils.helpers import format_screen_time


# Professional Muted Palette (Blues, Slate, Soft Emerald, Warm Amber)
WELLBEING_PALETTE = [
    "#2563EB",  # Professional Desktop Blue
    "#38BDF8",  # Muted Sky Blue
    "#10B981",  # Soft Emerald
    "#64748B",  # Slate
    "#F59E0B",  # Muted Amber
    "#6366F1",  # Indigo
    "#0284C7",  # Deep Sky
    "#94A3B8",  # Light Slate
]


class WellbeingRingChart(QWidget):
    """
    Circular screen time donut chart with clean, realistic Windows aesthetic.
    Displays total screen time today in center and clean app segments around the ring.
    """

    app_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._total_seconds: float = 0.0
        self._apps_data: List[Dict[str, Any]] = []
        self._center_title: str = "0 min"
        self._center_subtitle: str = "Screen time today"
        self._sync_status: str = "Synced"

    def set_data(self, total_seconds: float, apps: List[Dict[str, Any]], sync_time: str = ""):
        """Update chart with screen time totals and top applications."""
        self._total_seconds = max(total_seconds, 0.0)
        self._apps_data = apps or []
        self._center_title = format_screen_time(self._total_seconds)
        if sync_time:
            self._sync_status = f"Synced {sync_time}"
        self.update()

    def paintEvent(self, event):
        """Paint clean, professional circular donut ring."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 16
        cx = w / 2.0
        cy = h / 2.0
        radius = size / 2.0
        ring_thickness = 16.0

        rect = QRectF(cx - radius + ring_thickness / 2.0,
                      cy - radius + ring_thickness / 2.0,
                      size - ring_thickness,
                      size - ring_thickness)

        # 1. Background ring track (clean solid slate-graphite)
        track_color = QColor(COLORS["bg_medium"])
        track_pen = QPen(track_color, ring_thickness, Qt.SolidLine, Qt.FlatCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # 2. Draw colored app segments
        if self._total_seconds > 0 and self._apps_data:
            start_angle = 90.0 * 16.0  # 12 o'clock
            gap_angle = 1.5 * 16.0

            top_apps = self._apps_data[:6]
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

                actual_span = span_angle
                if len(segments) > 1 and abs(actual_span) > gap_angle:
                    actual_span = span_angle + (gap_angle if span_angle < 0 else -gap_angle)

                color_hex = WELLBEING_PALETTE[i % len(WELLBEING_PALETTE)]
                seg_pen = QPen(QColor(color_hex), ring_thickness, Qt.SolidLine, Qt.FlatCap)
                painter.setPen(seg_pen)
                painter.drawArc(rect, int(start_angle), int(actual_span))

                start_angle += span_angle

        # 3. Center Text (Clean typography)
        # Status
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 9, QFont.Normal))
        painter.drawText(QRectF(cx - 70, cy - radius * 0.42, 140, 16), Qt.AlignCenter, f"● {self._sync_status}")

        # Big clean screen time value
        painter.setPen(QColor(COLORS["text_primary"]))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.drawText(QRectF(cx - 80, cy - radius * 0.18, 160, 30), Qt.AlignCenter, self._center_title)

        # Subtitle
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(QFont("Segoe UI", 10, QFont.Normal))
        painter.drawText(QRectF(cx - 70, cy + radius * 0.22, 140, 18), Qt.AlignCenter, self._center_subtitle)

        painter.end()


class LiveActiveAppCard(QFrame):
    """Compact card displaying currently active application and focus stopwatch."""

    set_limit_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
        )
        self._current_app_id = ""
        self._current_app_name = "Desktop"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)

        self.pulse_label = QLabel("ACTIVE WINDOW")
        self.pulse_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent;"
        )
        header.addWidget(self.pulse_label)
        header.addStretch()

        self.btn_limit = QPushButton("Set Limit")
        self.btn_limit.setCursor(Qt.PointingHandCursor)
        self.btn_limit.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 3px 8px; font-size: 11px; }} "
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['accent_primary']}; }}"
        )
        self.btn_limit.clicked.connect(self._on_limit_click)
        header.addWidget(self.btn_limit)
        layout.addLayout(header)

        # Main Info Row
        content_row = QHBoxLayout()
        content_row.setSpacing(10)

        self.icon_badge = QLabel("▪")
        self.icon_badge.setFixedSize(34, 34)
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setStyleSheet(
            f"background-color: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; font-size: 16px; color: {COLORS['accent_primary']};"
        )
        content_row.addWidget(self.icon_badge)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(1)

        self.app_title = QLabel("Desktop")
        self.app_title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        info_vbox.addWidget(self.app_title)

        self.category_label = QLabel("System")
        self.category_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        info_vbox.addWidget(self.category_label)
        content_row.addLayout(info_vbox, 1)

        # Stopwatch
        timer_vbox = QVBoxLayout()
        timer_vbox.setSpacing(1)
        timer_vbox.setAlignment(Qt.AlignRight)

        self.stopwatch_label = QLabel("00:00:00")
        self.stopwatch_label.setStyleSheet(
            f"font-size: 17px; font-weight: 700; font-family: 'Segoe UI', 'Consolas', monospace; "
            f"color: {COLORS['accent_secondary']}; border: none; background: transparent;"
        )
        timer_vbox.addWidget(self.stopwatch_label, 0, Qt.AlignRight)

        self.session_sub = QLabel("Current Session")
        self.session_sub.setStyleSheet(
            f"font-size: 10px; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        timer_vbox.addWidget(self.session_sub, 0, Qt.AlignRight)
        content_row.addLayout(timer_vbox)

        layout.addLayout(content_row)

        # Cumulative line
        self.cumul_label = QLabel("Today: 0 min")
        self.cumul_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; border-top: 1px solid {COLORS['border']}; "
            f"padding-top: 6px; margin-top: 2px; background: transparent;"
        )
        layout.addWidget(self.cumul_label)

    def update_tick(self, tick_data: Dict[str, Any]):
        """Update live foreground app details."""
        app_id = tick_data.get("app_id", "")
        app_name = tick_data.get("app_name", "Unknown")
        category = tick_data.get("category", "General")
        is_idle = tick_data.get("is_idle", False)
        session_sec = int(tick_data.get("session_seconds", 0))
        today_sec = tick_data.get("app_today_seconds", 0)

        self._current_app_id = app_id
        self._current_app_name = app_name

        if is_idle:
            self.pulse_label.setText("SCREEN TIME PAUSED")
            self.pulse_label.setStyleSheet(
                f"color: {COLORS['severity_warning']}; font-size: 10px; font-weight: 700; border: none; background: transparent;"
            )
            self.stopwatch_label.setStyleSheet(
                f"font-size: 17px; font-weight: 700; font-family: 'Segoe UI', monospace; "
                f"color: {COLORS['severity_warning']}; border: none; background: transparent;"
            )
            self.app_title.setText("Idle / Away")
            self.category_label.setText("Inactive for 2+ minutes")
            self.icon_badge.setText("●")
            self.cumul_label.setText("Tracking resumes on user input")
            self.btn_limit.setVisible(False)
        else:
            self.pulse_label.setText("ACTIVE WINDOW")
            self.pulse_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; border: none; background: transparent;"
            )
            self.stopwatch_label.setStyleSheet(
                f"font-size: 17px; font-weight: 700; font-family: 'Segoe UI', monospace; "
                f"color: {COLORS['accent_secondary']}; border: none; background: transparent;"
            )
            self.app_title.setText(app_name)
            self.category_label.setText(category)
            self.btn_limit.setVisible(bool(app_id and app_id != "idle"))

            cat_symbols = {
                "Browser": "🌐",
                "Developer Tool": "💻",
                "Productivity": "📝",
                "Communication": "💬",
                "Media": "🎵",
                "Gaming": "🎮",
                "Creative": "🎨",
                "System": "⚙️",
            }
            self.icon_badge.setText(cat_symbols.get(category, "▪"))

            hrs = session_sec // 3600
            mins = (session_sec % 3600) // 60
            secs = session_sec % 60
            self.stopwatch_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

            cumul_text = format_screen_time(today_sec, detailed=True)
            self.cumul_label.setText(f"Today: {cumul_text}")

    def _on_limit_click(self):
        if self._current_app_id:
            self.set_limit_requested.emit(self._current_app_id, self._current_app_name)


class AppUsageRowWidget(QFrame):
    """Compact row for app screen time breakdown."""

    set_limit_clicked = Signal(str, str)

    def __init__(self, app_data: Dict[str, Any], color_hex: str, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.color_hex = color_hex
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; }} "
            f"QFrame:hover {{ border-color: {COLORS['border_light']}; background-color: {COLORS['bg_hover']}; }}"
        )
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 1. Subtle color dot
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background-color: {self.color_hex}; border-radius: 4px; border: none;")
        layout.addWidget(dot)

        # 2. App Name & Category
        info_col = QVBoxLayout()
        info_col.setSpacing(1)

        app_name = self.app_data.get("app_name", "Application")
        title_label = QLabel(app_name)
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        info_col.addWidget(title_label)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)

        cat_lbl = QLabel(self.app_data.get("category", "General"))
        cat_lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; border: none;")
        sub_row.addWidget(cat_lbl)

        launches = self.app_data.get("launches", 0)
        launches_label = QLabel(f"• {launches} open{'s' if launches != 1 else ''}")
        launches_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; border: none;")
        sub_row.addWidget(launches_label)
        sub_row.addStretch()

        info_col.addLayout(sub_row)
        layout.addLayout(info_col, 3)

        # 3. Usage bar + duration
        bar_col = QVBoxLayout()
        bar_col.setSpacing(3)

        pct = self.app_data.get("percentage", 0.0)
        dur_sec = self.app_data.get("duration_seconds", 0.0)
        dur_text = format_screen_time(dur_sec)

        dur_label = QLabel(f"{dur_text}  ({pct:.1f}%)")
        dur_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        dur_label.setAlignment(Qt.AlignRight)
        bar_col.addWidget(dur_label)

        # Progress bar
        bar_bg = QFrame()
        bar_bg.setFixedHeight(4)
        bar_bg.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-radius: 2px; border: none;")
        bar_layout = QHBoxLayout(bar_bg)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        bar_fill = QFrame()
        bar_fill.setFixedHeight(4)
        bar_fill.setFixedWidth(min(max(int(pct * 2.0), 3), 180))
        bar_fill.setStyleSheet(f"background-color: {self.color_hex}; border-radius: 2px; border: none;")
        bar_layout.addWidget(bar_fill)
        bar_layout.addStretch()

        bar_col.addWidget(bar_bg)
        layout.addLayout(bar_col, 2)

        # 4. Limit Badge / Action Button
        limit_mins = self.app_data.get("daily_limit_minutes")
        limit_enabled = self.app_data.get("limit_enabled")

        btn_limit = QPushButton()
        btn_limit.setCursor(Qt.PointingHandCursor)

        if limit_mins and limit_enabled:
            limit_sec = limit_mins * 60.0
            if dur_sec >= limit_sec:
                btn_limit.setText(f"Limit Reached ({limit_mins}m)")
                btn_limit.setStyleSheet(
                    f"QPushButton {{ background-color: #3B181B; color: {COLORS['severity_error']}; "
                    f"border: 1px solid {COLORS['severity_error']}; border-radius: 4px; padding: 3px 6px; font-size: 10px; font-weight: 600; }} "
                    f"QPushButton:hover {{ background-color: {COLORS['severity_error']}; color: white; }}"
                )
            else:
                rem_mins = int((limit_sec - dur_sec) // 60)
                btn_limit.setText(f"{rem_mins}m of {limit_mins}m left")
                btn_limit.setStyleSheet(
                    f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['accent_secondary']}; "
                    f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; padding: 3px 6px; font-size: 10px; }} "
                    f"QPushButton:hover {{ border-color: {COLORS['accent_secondary']}; }}"
                )
        else:
            btn_limit.setText("Set Limit")
            btn_limit.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {COLORS['text_muted']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 3px 6px; font-size: 10px; }} "
                f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['border_light']}; }}"
            )

        btn_limit.clicked.connect(lambda: self.set_limit_clicked.emit(
            self.app_data.get("app_id", ""), self.app_data.get("app_name", "")
        ))
        layout.addWidget(btn_limit)


class DailyLimitDialog(QDialog):
    """Clean Windows dialog for setting daily screen time limit."""

    def __init__(self, app_id: str, app_name: str, current_limit_mins: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.app_name = app_name
        self.setWindowTitle(f"Daily Limit — {app_name}")
        self.setFixedSize(360, 240)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']}; color: {COLORS['text_primary']};")

        self.limit_minutes: int = current_limit_mins or 60
        self.remove_requested: bool = False
        self._setup_ui(current_limit_mins)

    def _setup_ui(self, current_limit_mins):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel(f"Daily Limit — {self.app_name}")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']};")
        layout.addWidget(title)

        desc = QLabel(f"Set a daily threshold to receive notifications when exceeded.")
        desc.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
        layout.addWidget(desc)

        # Quick preset buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        for mins, label in [(15, "15m"), (30, "30m"), (45, "45m"), (60, "1h"), (120, "2h")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 8px; font-size: 11px; }} "
                f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['accent_primary']}; }}"
            )
            btn.clicked.connect(lambda ch, m=mins: self.spin_mins.setValue(m))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        # Custom spinbox
        spin_row = QHBoxLayout()
        spin_label = QLabel("Daily limit (minutes):")
        spin_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        spin_row.addWidget(spin_label)

        self.spin_mins = QSpinBox()
        self.spin_mins.setRange(1, 1440)
        self.spin_mins.setValue(current_limit_mins or 60)
        self.spin_mins.setStyleSheet(
            f"QSpinBox {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 6px; }}"
        )
        spin_row.addWidget(self.spin_mins)
        layout.addLayout(spin_row)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()
        if current_limit_mins:
            btn_remove = QPushButton("Remove")
            btn_remove.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {COLORS['severity_error']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 6px 12px; font-size: 12px; }} "
                f"QPushButton:hover {{ background-color: {COLORS['severity_error']}; color: white; }}"
            )
            btn_remove.clicked.connect(self._on_remove)
            btn_layout.addWidget(btn_remove)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.setProperty("class", "primary")
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
    """Clean widget for focus session management and bedtime schedule."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; }}"
        )
        self._focus_remaining_seconds: int = 25 * 60
        self._focus_active: bool = False
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._on_focus_tick)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Focus & Bedtime")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; border: none;")
        header.addWidget(title)
        header.addStretch()

        bedtime = QLabel("Bedtime: 11 PM – 7 AM")
        bedtime.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; border: none;")
        header.addWidget(bedtime)
        layout.addLayout(header)

        # Timer Row
        timer_box = QHBoxLayout()
        timer_box.setSpacing(10)

        self.timer_label = QLabel("25:00")
        self.timer_label.setStyleSheet(
            f"font-size: 22px; font-weight: 700; font-family: 'Segoe UI', monospace; "
            f"color: {COLORS['text_primary']}; border: none; background: transparent;"
        )
        timer_box.addWidget(self.timer_label)

        self.btn_toggle = QPushButton("Start (25m)")
        self.btn_toggle.setProperty("class", "primary")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle_focus)
        timer_box.addWidget(self.btn_toggle)

        btn_reset = QPushButton("Reset")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_focus)
        timer_box.addWidget(btn_reset)

        timer_box.addStretch()
        layout.addLayout(timer_box)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        lbl = QLabel("Presets:")
        lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; border: none;")
        presets_layout.addWidget(lbl)

        for mins in [15, 25, 45, 60]:
            p_btn = QPushButton(f"{mins}m")
            p_btn.setCursor(Qt.PointingHandCursor)
            p_btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text_muted']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 6px; font-size: 10px; }} "
                f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['border_light']}; }}"
            )
            p_btn.clicked.connect(lambda ch, m=mins: self._set_focus_duration(m))
            presets_layout.addWidget(p_btn)

        presets_layout.addStretch()
        layout.addLayout(presets_layout)

    def _toggle_focus(self):
        if not self._focus_active:
            self._focus_active = True
            self._focus_timer.start(1000)
            self.btn_toggle.setText("Pause")
        else:
            self._focus_active = False
            self._focus_timer.stop()
            self.btn_toggle.setText("Resume")

    def _reset_focus(self):
        self._focus_active = False
        self._focus_timer.stop()
        self._focus_remaining_seconds = 25 * 60
        self._update_display()
        self.btn_toggle.setText("Start (25m)")

    def _set_focus_duration(self, minutes: int):
        self._focus_active = False
        self._focus_timer.stop()
        self._focus_remaining_seconds = minutes * 60
        self._update_display()
        self.btn_toggle.setText(f"Start ({minutes}m)")

    def _on_focus_tick(self):
        if self._focus_remaining_seconds > 0:
            self._focus_remaining_seconds -= 1
            self._update_display()
        else:
            self._focus_active = False
            self._focus_timer.stop()
            self.btn_toggle.setText("Done")

    def _update_display(self):
        mins = self._focus_remaining_seconds // 60
        secs = self._focus_remaining_seconds % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")


class HourlyScreenTimeChart(QWidget):
    """Clean bar chart for 24-hour screen time breakdown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.setMinimumWidth(240)
        self._data: Dict[int, float] = {h: 0.0 for h in range(24)}
        self._max_seconds: float = 3600.0

    def set_data(self, hourly_map: Dict[int, float]):
        """Set screen time data per hour in seconds."""
        self._data = hourly_map or {h: 0.0 for h in range(24)}
        max_val = max(self._data.values()) if self._data else 0.0
        self._max_seconds = max(max_val, 1800.0)
        self.update()

    def paintEvent(self, event):
        """Paint clean, solid bars with highlight on current hour."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_bottom = 20
        padding_top = 8
        padding_sides = 8

        chart_w = w - 2 * padding_sides
        chart_h = h - padding_bottom - padding_top

        current_hour = datetime.now().hour
        bar_gap = 2
        bar_w = max((chart_w / 24.0) - bar_gap, 2.0)

        for hour in range(24):
            sec = self._data.get(hour, 0.0)
            bar_height = max((sec / self._max_seconds) * chart_h, 2.0) if self._max_seconds > 0 else 2.0
            x = padding_sides + hour * (bar_w + bar_gap)
            y = padding_top + chart_h - bar_height

            is_now = (hour == current_hour)
            bar_color = QColor(COLORS["accent_secondary"] if is_now else COLORS["accent_primary"])
            if sec == 0:
                bar_color = QColor(COLORS["bg_medium"])

            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_height), 1, 1)

            if hour % 4 == 0 or hour == 23:
                painter.setPen(QColor(COLORS["text_muted"]))
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(QRectF(x - 6, h - padding_bottom + 2, bar_w + 12, 16), Qt.AlignCenter, f"{hour:02d}")

        painter.end()
