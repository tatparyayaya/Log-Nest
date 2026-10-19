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
    QPushButton, QSizePolicy, QScrollArea, QFileIconProvider, QStyle
)
from PySide6.QtCore import (
    Qt, Signal, QSize, QTimer, QFileInfo, QEvent
)
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QIcon, QImage, QPixmap

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


from functools import lru_cache


def ui_is_presented(widget):
    """Check the actual host window as well as embedded page visibility."""
    if not widget.isVisible():
        return False
    root = widget.window()
    proxy = root.graphicsProxyWidget()
    if proxy is not None and proxy.scene() is not None:
        return any(view.isVisible() and not view.window().isMinimized()
                   for view in proxy.scene().views())
    return not root.isMinimized()


@lru_cache(maxsize=128)
def _application_icon(executable, modified):
    """Bounded native-icon cache; file modification time invalidates updates."""
    icon = QFileIconProvider().icon(QFileInfo(executable))
    try:
        import win32gui
        large, small = win32gui.ExtractIconEx(executable, 0)
        try:
            handles = large or small
            if handles:
                image = QImage.fromHICON(handles[0])
                if not image.isNull(): icon = QIcon(QPixmap.fromImage(image))
        finally:
            for handle in large + small: win32gui.DestroyIcon(handle)
    except Exception:
        pass
    return icon


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
        self.setMinimumHeight(110)
        self._list_viewport = None

        self._setup_ui()

    def _setup_ui(self):
        """Reference timeline row: content left, severity and age right."""
        self.setObjectName("eventRow")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet(
            "QFrame#eventRow{background:#0b1017;border:1px solid #213044;border-radius:12px;padding:0}"
            "QFrame#eventRow:hover,QFrame#eventRow:focus{background:#1c2b44;border-color:#263a56}"
        )
        raw = self.event_data.get("metadata")
        metadata = raw if isinstance(raw, dict) else (safe_json_loads(raw) or {})
        application = bool(metadata.get("opened_at")) or self.event_data.get("category") == "Application"
        accent = "#8064ed" if application else "#60bfda"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30,24,30,24)
        layout.setSpacing(18)
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(f"background:{accent};border:none;border-radius:2px")
        layout.addWidget(bar)
        executable = metadata.get("executable") or metadata.get("exe_path")
        file = QFileInfo(executable) if executable else QFileInfo()
        icon = _application_icon(file.absoluteFilePath(), file.lastModified().toMSecsSinceEpoch()) if file.isFile() else QIcon()
        severity = self.event_data.get("severity", "info")
        if icon.isNull():
            native = QStyle.SP_MessageBoxWarning if severity == "warning" else QStyle.SP_MessageBoxCritical if severity in ("error","critical") else QStyle.SP_ComputerIcon
            icon = self.style().standardIcon(native)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(34,34)
        self.icon_label.setPixmap(icon.pixmap(28,28))
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background:transparent;border:none")
        layout.addWidget(self.icon_label)
        content = QVBoxLayout()
        content.setSpacing(7)
        content.addStretch()
        def text_label(text,size,color):
            label = QLabel(text)
            label.setTextFormat(Qt.PlainText)
            label.setStyleSheet(f"font-family:Segoe UI;font-size:{size}px;color:{color};background:transparent;border:none")
            label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
            label.setToolTip(text)
            return label
        title = text_label(self.event_data.get("title","Unknown Event"),16,"#d7e5f5")
        content.addWidget(title)
        description = self.event_data.get("description", "").split("\n")[0]
        if metadata.get("opened_at"):
            from datetime import datetime
            def clock(value):
                try: return datetime.fromisoformat(value).strftime("%I:%M %p")
                except (TypeError, ValueError): return str(value or "")
            description = f"Opened: {clock(metadata['opened_at'])}"
            description += f"  |  Closed: {clock(metadata['closed_at'])}" if metadata.get('closed_at') else "  |  Running"
        if description:
            content.addWidget(text_label(description,13,"#859ab9"))
        source_row = QHBoxLayout()
        source_row.setSpacing(7)
        source = self.event_data.get("source", "")
        if source:
            small_icon = QLabel()
            small_icon.setFixedSize(16,16)
            small_icon.setPixmap(icon.pixmap(14,14))
            small_icon.setStyleSheet("background:transparent;border:none")
            source_row.addWidget(small_icon)
            source_label = text_label(source,12,"#738aa9")
            source_label.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Preferred)
            source_row.addWidget(source_label)
        if metadata.get("duration_formatted"):
            duration = QLabel(str(metadata['duration_formatted']))
            duration.setStyleSheet("background:#3a642e;color:#c1d4b1;border:none;border-radius:3px;padding:2px 8px;font-size:11px")
            source_row.addWidget(duration)
        source_row.addStretch()
        content.addLayout(source_row)
        content.addStretch()
        layout.addLayout(content,1)
        right = QVBoxLayout()
        right.setSpacing(14)
        right.addStretch()
        badge = QLabel(severity.upper())
        bg,fg = {"info":("#435e35","#9bc6da"),"warning":("#7f3822","#f4b35f"),"error":("#752d38","#f4a0a7"),"critical":("#752d38","#f4a0a7")}.get(severity,("#435e35","#9bc6da"))
        badge.setStyleSheet(f"background:{bg};color:{fg};border:none;border-radius:4px;padding:5px 12px;font-size:11px")
        right.addWidget(badge,0,Qt.AlignRight)
        right.addStretch()
        age = QLabel(relative_time(self.event_data.get("timestamp","")))
        age.setStyleSheet("font-size:12px;color:#8191a9;background:transparent;border:none")
        self._age_label = age
        right.addWidget(age,0,Qt.AlignRight)
        right.addStretch()
        layout.addLayout(right)

    def refresh_relative_time(self):
        self._age_label.setText(relative_time(self.event_data.get("timestamp", "")))

    def showEvent(self, event):
        super().showEvent(event)
        ancestor = self.parentWidget()
        while ancestor is not None and not isinstance(ancestor, QScrollArea):
            ancestor = ancestor.parentWidget()
        if ancestor is not None:
            viewport = ancestor.viewport()
            if viewport is not self._list_viewport:
                self._list_viewport = viewport
                viewport.installEventFilter(self)
            self._fit_row()

    def _fit_row(self):
        if self._list_viewport is not None:
            layout = self.parentWidget().layout()
            gap = max(0, layout.spacing()) if layout else 8
            margins = layout.contentsMargins() if layout else None
            inset = margins.top() + margins.bottom() if margins else 0
            self.setFixedHeight(max(110, (self._list_viewport.height() - inset - 3 * gap) // 4))

    def eventFilter(self, watched, event):
        if watched is self._list_viewport and event.type() == QEvent.Resize:
            self._fit_row()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        """Emit clicked signal on card click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)


class TimelineEventCard(EventCard):
    """Reference styling and four-row sizing confined to the timeline list."""

    def __init__(self, event_data, parent=None):
        super().__init__(event_data, parent)
        self.setMinimumHeight(0)
        raw = event_data.get("metadata")
        metadata = raw if isinstance(raw, dict) else (safe_json_loads(raw) or {})
        if metadata.get("opened_at") or event_data.get("category") == "Application":
            self.setStyleSheet(self.styleSheet().replace("background:#0b1017", "background:#1c2b44"))

    def _fit_row(self):
        if self._list_viewport is None:
            return
        layout = self.parentWidget().layout()
        gap = max(0, layout.spacing()) if layout else 8
        margins = layout.contentsMargins() if layout else None
        inset = margins.top() + margins.bottom() if margins else 0
        height = max(1, (self._list_viewport.height() - inset - 3 * gap) // 4)
        self.setFixedHeight(height)
        padding = min(24, max(8, height // 7))
        self.layout().setContentsMargins(30, padding, 30, padding)


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
