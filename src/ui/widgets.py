"""
LOG NEST - Custom Widgets
Reusable UI components for the application.
"""

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, Signal, QSize, QTimer
)
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient

from src.ui.theme import COLORS, severity_badge_style, category_color
from src.utils.helpers import (
    relative_time, format_timestamp, get_event_icon,
    safe_json_loads, format_bytes, truncate_path
)


class StatCard(QFrame):
    """Dashboard statistic card with icon, value, and label."""

    def __init__(self, icon_text, label, value="0", accent_color=None,
                 parent=None):
        super().__init__(parent)
        self.setProperty("class", "stat-card")
        self.setStyleSheet(self.styleSheet())  # Force style refresh
        self.setCursor(Qt.PointingHandCursor)

        color = accent_color or COLORS["accent_primary"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Icon row
        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(
            f"font-size: 28px; color: {color}; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(icon_label)

        # Value
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self.value_label)

        # Label
        label_widget = QLabel(label.upper())
        label_widget.setStyleSheet(
            f"font-size: 11px; font-weight: 600; "
            f"color: {COLORS['text_secondary']}; letter-spacing: 1px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(label_widget)

        layout.addStretch()

        # Accent bar at top
        self._accent_color = color
        self.setMinimumHeight(140)
        self.setMinimumWidth(180)

    def set_value(self, value):
        """Update the displayed value."""
        self.value_label.setText(str(value))

    def paintEvent(self, event):
        """Custom paint to add accent gradient bar at top."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Top accent bar
        color = QColor(self._accent_color)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, color)
        color.setAlpha(80)
        gradient.setColorAt(1, color)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(0, 0, self.width(), 4, 2, 2)
        painter.end()


class EventCard(QFrame):
    """Card displaying a single event in the timeline."""

    clicked = Signal(dict)
    context_requested = Signal(int)  # event_id

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(80)

        self._setup_ui()

    def _setup_ui(self):
        """Build the event card UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Category color bar
        cat = self.event_data.get("category", "")
        cat_color = category_color(cat)

        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        color_bar.setStyleSheet(
            f"background-color: {cat_color}; border-radius: 2px; border: none;"
        )
        layout.addWidget(color_bar)

        # Icon
        icon_text = get_event_icon(self.event_data.get("event_type", ""))
        icon_label = QLabel(icon_text)
        icon_label.setFixedWidth(32)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"font-size: 18px; color: {cat_color}; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title_label = QLabel(self.event_data.get("title", "Unknown Event"))
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; "
            f"background: transparent; border: none;"
        )
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)

        # Severity badge
        severity = self.event_data.get("severity", "info")
        sev_label = QLabel(severity.upper())
        sev_label.setStyleSheet(severity_badge_style(severity))
        sev_label.setFixedHeight(22)
        title_row.addWidget(sev_label)

        content_layout.addLayout(title_row)

        # Description (truncated)
        desc = self.event_data.get("description", "")
        if desc:
            # Show first line only
            first_line = desc.split("\n")[0][:120]
            desc_label = QLabel(first_line)
            desc_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 12px; "
                f"background: transparent; border: none;"
            )
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)

        # Bottom row: source + duration + time
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        metadata = safe_json_loads(self.event_data.get("metadata")) or {}
        category = self.event_data.get("category", "")
        source = metadata.get("app_name") or self.event_data.get("source", "")

        if source:
            source_icon = "🖥️" if category == "Application" else "📍"
            source_text = truncate_path(source, 50)
            source_label = QLabel(f"{source_icon} {source_text}")
            source_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 11px; "
                f"background: transparent; border: none;"
            )
            bottom_row.addWidget(source_label)

        if metadata.get("duration_formatted"):
            dur_text = metadata.get("duration_formatted")
            dur_badge = QLabel(f"⏱ {dur_text}")
            dur_badge.setStyleSheet(
                f"background-color: {COLORS['accent_primary']}22; color: {COLORS['accent_primary']}; "
                f"border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: 600;"
            )
            bottom_row.addWidget(dur_badge)

        bottom_row.addStretch()

        timestamp = self.event_data.get("timestamp", "")
        time_text = relative_time(timestamp)
        time_label = QLabel(f"🕐 {time_text}")
        time_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        bottom_row.addWidget(time_label)

        content_layout.addLayout(bottom_row)

        layout.addLayout(content_layout, 1)

    def mousePressEvent(self, event):
        """Handle click to show event details."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Hover effect."""
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_hover']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 12px; }}"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Remove hover effect."""
        self.setStyleSheet("")
        super().leaveEvent(event)


class ActivityChart(QWidget):
    """Simple bar chart showing hourly activity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}  # hour_str -> count
        self._max_value = 1
        self.setMinimumHeight(160)
        self.setMinimumWidth(300)

    def set_data(self, hourly_data):
        """Set chart data. hourly_data: dict of hour_str -> count."""
        self._data = hourly_data
        self._max_value = max(hourly_data.values()) if hourly_data else 1
        self.update()

    def paintEvent(self, event):
        """Custom paint the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_bottom = 30
        padding_top = 10
        padding_sides = 10

        chart_w = w - 2 * padding_sides
        chart_h = h - padding_bottom - padding_top

        if not self._data:
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                self.rect(), Qt.AlignCenter, "No activity data yet"
            )
            painter.end()
            return

        # Draw bars
        hours = sorted(self._data.keys())
        num_bars = max(len(hours), 1)
        bar_width = max(chart_w / num_bars - 4, 4)
        gap = 4

        accent = QColor(COLORS["accent_primary"])

        for i, hour in enumerate(hours):
            count = self._data[hour]
            bar_h = max(
                int((count / self._max_value) * chart_h), 3
            ) if self._max_value > 0 else 3

            x = padding_sides + i * (bar_width + gap)
            y = padding_top + chart_h - bar_h

            # Gradient bar
            gradient = QLinearGradient(x, y, x, y + bar_h)
            gradient.setColorAt(0, accent)
            accent_dark = QColor(accent)
            accent_dark.setAlpha(120)
            gradient.setColorAt(1, accent_dark)

            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(
                int(x), int(y), int(bar_width), int(bar_h), 3, 3
            )

            # Hour label
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont("Segoe UI", 8))
            label_rect = painter.boundingRect(
                int(x), int(h - padding_bottom + 5),
                int(bar_width), 20, Qt.AlignCenter, hour
            )
            painter.drawText(label_rect, Qt.AlignCenter, hour)

        painter.end()


class PulsingDot(QWidget):
    """Small pulsing dot indicator for live status."""

    def __init__(self, color="#00D4AA", size=10, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self._pulse_alpha = 255
        self.setFixedSize(size + 8, size + 8)

        # Pulse animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)
        self._direction = -5

    def _animate(self):
        self._pulse_alpha += self._direction
        if self._pulse_alpha <= 100:
            self._direction = 5
        elif self._pulse_alpha >= 255:
            self._direction = -5
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Outer glow
        glow = QColor(self._color)
        glow.setAlpha(int(self._pulse_alpha * 0.3))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        cx, cy = self.width() // 2, self.height() // 2
        painter.drawEllipse(
            cx - self._size // 2 - 2, cy - self._size // 2 - 2,
            self._size + 4, self._size + 4
        )

        # Core dot
        core = QColor(self._color)
        core.setAlpha(self._pulse_alpha)
        painter.setBrush(core)
        painter.drawEllipse(
            cx - self._size // 2, cy - self._size // 2,
            self._size, self._size
        )
        painter.end()


class CategoryBadge(QLabel):
    """Small colored badge for event categories."""

    def __init__(self, category, parent=None):
        super().__init__(category, parent)
        color = category_color(category)
        self.setStyleSheet(
            f"background-color: {color}22; color: {color}; "
            f"border: 1px solid {color}44; border-radius: 4px; "
            f"padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )
        self.setFixedHeight(22)
