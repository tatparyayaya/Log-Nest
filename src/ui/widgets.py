"""
LOG NEST - Professional Windows Custom Widgets
Compact, clean desktop components:
- Compact StatCard with subtle indicator
- Clean EventCard for timeline entries
- Refined solid ActivityChart
- Calm status indicator
"""

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QSize, QTimer
)
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from src.ui.theme import COLORS, severity_badge_style, category_color
from src.utils.helpers import (
    relative_time, format_timestamp, get_event_icon,
    safe_json_loads, format_bytes, truncate_path
)


class StatCard(QFrame):
    """Compact Windows-style statistic metric card."""

    def __init__(self, icon_text, label, value="0", accent_color=None, parent=None):
        super().__init__(parent)
        self.setProperty("class", "stat-card")
        self.setCursor(Qt.PointingHandCursor)

        color = accent_color or COLORS["accent_primary"]
        self._accent_color = color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Header row: label on left, minimal icon on right
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        label_widget = QLabel(label.upper())
        label_widget.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {COLORS['text_muted']}; "
            f"letter-spacing: 0.5px; background: transparent; border: none;"
        )
        header_row.addWidget(label_widget)
        header_row.addStretch()

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(
            f"font-size: 13px; color: {color}; background: transparent; border: none;"
        )
        header_row.addWidget(icon_label)
        layout.addLayout(header_row)

        # Value
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self.value_label)

        self.setMinimumHeight(66)
        self.setMinimumWidth(130)

    def set_value(self, value):
        """Update the displayed value."""
        self.value_label.setText(str(value))

    def paintEvent(self, event):
        """Paint subtle solid 2px accent line at top."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self._accent_color)
        color.setAlpha(160)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(0, 0, self.width(), 2, 1, 1)
        painter.end()


class EventCard(QFrame):
    """Compact card displaying a single event in the timeline."""

    clicked = Signal(dict)
    context_requested = Signal(int)  # event_id

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(58)

        self._setup_ui()

    def _setup_ui(self):
        """Build the compact event card UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Category color bar
        cat = self.event_data.get("category", "")
        cat_color = category_color(cat)

        color_bar = QFrame()
        color_bar.setFixedWidth(3)
        color_bar.setStyleSheet(
            f"background-color: {cat_color}; border-radius: 1px; border: none;"
        )
        layout.addWidget(color_bar)

        # Icon
        icon_text = get_event_icon(self.event_data.get("event_type", ""))
        icon_label = QLabel(icon_text)
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"font-size: 14px; color: {cat_color}; background: transparent; border: none;"
        )
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title_label = QLabel(self.event_data.get("title", "Unknown Event"))
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']}; "
            f"background: transparent; border: none;"
        )
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)

        # Severity badge
        severity = self.event_data.get("severity", "info")
        sev_label = QLabel(severity.upper())
        sev_label.setStyleSheet(severity_badge_style(severity))
        sev_label.setFixedHeight(20)
        title_row.addWidget(sev_label)

        # Duration badge if present in metadata
        metadata = safe_json_loads(self.event_data.get("metadata")) or {}
        if metadata.get("duration_formatted"):
            dur_label = QLabel(metadata["duration_formatted"])
            dur_label.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; color: {COLORS['accent_secondary']}; "
                f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
                f"padding: 1px 6px; font-size: 10px; font-weight: 600;"
            )
            title_row.addWidget(dur_label)

        content_layout.addLayout(title_row)

        # Subtitle: time and source
        sub_row = QHBoxLayout()
        sub_row.setSpacing(8)

        ts = self.event_data.get("timestamp", "")
        time_label = QLabel(relative_time(ts))
        time_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; border: none; background: transparent;"
        )
        sub_row.addWidget(time_label)

        source = self.event_data.get("source", "")
        if source:
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
            sub_row.addWidget(dot)

            source_label = QLabel(source)
            source_label.setStyleSheet(
                f"font-size: 11px; color: {COLORS['text_secondary']}; border: none; background: transparent;"
            )
            sub_row.addWidget(source_label)

        sub_row.addStretch()
        content_layout.addLayout(sub_row)

        layout.addLayout(content_layout, 1)

    def mousePressEvent(self, event):
        """Emit clicked signal on card click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)


class ActivityChart(QWidget):
    """Clean bar chart showing hourly activity with solid muted blue bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self._max_value = 1
        self.setMinimumHeight(130)
        self.setMinimumWidth(260)

    def set_data(self, hourly_data):
        """Set chart data."""
        self._data = hourly_data
        self._max_value = max(hourly_data.values()) if hourly_data else 1
        self.update()

    def paintEvent(self, event):
        """Paint clean, solid bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_bottom = 22
        padding_top = 8
        padding_sides = 8

        chart_w = w - 2 * padding_sides
        chart_h = h - padding_bottom - padding_top

        if not self._data:
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "No activity data yet")
            painter.end()
            return

        hours = sorted(self._data.keys())
        num_bars = max(len(hours), 1)
        bar_width = max(chart_w / num_bars - 3, 3)
        gap = 3

        accent = QColor(COLORS["accent_primary"])

        for i, hour in enumerate(hours):
            count = self._data[hour]
            bar_h = max(int((count / self._max_value) * chart_h), 2) if self._max_value > 0 else 2

            x = padding_sides + i * (bar_width + gap)
            y = padding_top + chart_h - bar_h

            painter.setPen(Qt.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_h), 2, 2)

            # Hour label
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                int(x), int(h - padding_bottom + 4),
                int(bar_width), 16, Qt.AlignCenter, hour
            )

        painter.end()


class PulsingDot(QWidget):
    """Calm status indicator dot (non-flashy, professional Windows style)."""

    def __init__(self, color="#38BDF8", size=8, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size + 6, size + 6)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() // 2, self.height() // 2

        # Outer subtle ring
        ring = QColor(self._color)
        ring.setAlpha(40)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ring)
        painter.drawEllipse(cx - self._size // 2 - 2, cy - self._size // 2 - 2, self._size + 4, self._size + 4)

        # Core solid dot
        core = QColor(self._color)
        painter.setBrush(core)
        painter.drawEllipse(cx - self._size // 2, cy - self._size // 2, self._size, self._size)
        painter.end()


class CategoryBadge(QLabel):
    """Small clean badge for event categories."""

    def __init__(self, category, parent=None):
        super().__init__(category, parent)
        color = category_color(category)
        self.setStyleSheet(
            f"background-color: {color}18; color: {color}; "
            f"border: 1px solid {color}33; border-radius: 4px; "
            f"padding: 1px 6px; font-size: 11px; font-weight: 500;"
        )
        self.setFixedHeight(20)
