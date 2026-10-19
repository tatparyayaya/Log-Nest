"""
LOG NEST - Timeline Page
Chronological event timeline with filters, live auto-refresh, and detail view.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QLineEdit,
    QDateEdit, QSizePolicy, QDialog, QTextEdit, QCheckBox,
    QGridLayout, QSplitter
)
from PySide6.QtCore import Qt, QTimer, QDate, Slot, Signal

from src.database import DatabaseManager
from src.ui.theme import COLORS, severity_badge_style, category_color
from src.ui.widgets import TimelineEventCard, CategoryBadge, ui_is_presented
from src.utils.helpers import (
    format_timestamp_full, safe_json_loads, format_bytes,
    EVENT_TYPE_LABELS, relative_time
)


class EventDetailDialog(QDialog):
    """Dialog showing full event details and surrounding context."""

    def __init__(self, event_data, db, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.db = db
        self.setWindowTitle("Event Details")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_dark']}; }}"
        )
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel(self.event_data.get("title", "Event"))
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {COLORS['text_primary']};"
        )
        title.setWordWrap(True)
        header.addWidget(title, 1)

        severity = self.event_data.get("severity", "info")
        sev_label = QLabel(severity.upper())
        sev_label.setStyleSheet(severity_badge_style(severity))
        sev_label.setFixedHeight(24)
        header.addWidget(sev_label)

        layout.addLayout(header)

        # Info grid
        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px;"
        )
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)

        metadata = safe_json_loads(self.event_data.get("metadata")) or {}

        fields = [
            ("Timestamp", format_timestamp_full(
                self.event_data.get("timestamp", ""))),
            ("Category", self.event_data.get("category", "")),
            ("Type", EVENT_TYPE_LABELS.get(
                self.event_data.get("event_type", ""),
                self.event_data.get("event_type", ""))),
            ("Application", metadata.get("app_name") or self.event_data.get("source", "")),
        ]

        if metadata.get("opened_at"):
            fields.append(("Opened At", format_timestamp_full(metadata.get("opened_at"))))
        if metadata.get("closed_at"):
            fields.append(("Closed At", format_timestamp_full(metadata.get("closed_at"))))
        if metadata.get("duration_formatted"):
            fields.append(("Session Duration", metadata.get("duration_formatted")))
        if metadata.get("peak_process_count") and metadata.get("peak_process_count") > 1:
            fields.append(("Subprocesses Coordinated", str(metadata.get("peak_process_count"))))
        if metadata.get("executable"):
            fields.append(("Executable Path", metadata.get("executable")))

        for i, (label, value) in enumerate(fields):
            lbl = QLabel(label + ":")
            lbl.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-weight: 600; "
                f"font-size: 12px; border: none;"
            )
            val = QLabel(str(value))
            val.setStyleSheet(
                f"color: {COLORS['text_primary']}; font-size: 13px; border: none;"
            )
            val.setWordWrap(True)
            info_layout.addWidget(lbl, i, 0)
            info_layout.addWidget(val, i, 1)

        layout.addWidget(info_frame)


        # Description
        desc = self.event_data.get("description", "")
        if desc:
            desc_label = QLabel("Description")
            desc_label.setStyleSheet(
                f"font-size: 14px; font-weight: 600; "
                f"color: {COLORS['text_primary']};"
            )
            layout.addWidget(desc_label)

            desc_text = QTextEdit()
            desc_text.setPlainText(desc)
            desc_text.setReadOnly(True)
            desc_text.setMaximumHeight(120)
            desc_text.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; "
                f"color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
                f"padding: 8px; font-family: 'Cascadia Code', 'Consolas', monospace;"
            )
            layout.addWidget(desc_text)

        # Metadata
        metadata = safe_json_loads(self.event_data.get("metadata"))
        if metadata:
            meta_label = QLabel("Metadata")
            meta_label.setStyleSheet(
                f"font-size: 14px; font-weight: 600; "
                f"color: {COLORS['text_primary']};"
            )
            layout.addWidget(meta_label)

            meta_text = QTextEdit()
            import json
            meta_text.setPlainText(json.dumps(metadata, indent=2))
            meta_text.setReadOnly(True)
            meta_text.setMaximumHeight(120)
            meta_text.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; "
                f"color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
                f"padding: 8px; font-family: 'Cascadia Code', 'Consolas', monospace;"
            )
            layout.addWidget(meta_text)

        # Context: events before and after
        event_id = self.event_data.get("id")
        if event_id:
            context = self.db.get_events_around(event_id, window_minutes=5)
            if context.get("before") or context.get("after"):
                ctx_label = QLabel("⏱  Context (±5 minutes)")
                ctx_label.setStyleSheet(
                    f"font-size: 14px; font-weight: 600; "
                    f"color: {COLORS['text_primary']};"
                )
                layout.addWidget(ctx_label)

                ctx_scroll = QScrollArea()
                ctx_scroll.setWidgetResizable(True)
                ctx_scroll.setMaximumHeight(200)
                ctx_scroll.setStyleSheet(
                    "QScrollArea { border: none; background: transparent; }"
                )

                ctx_widget = QWidget()
                ctx_layout = QVBoxLayout(ctx_widget)
                ctx_layout.setContentsMargins(0, 0, 0, 0)
                ctx_layout.setSpacing(4)

                for evt in reversed(context.get("before", [])):
                    row = self._make_context_row(evt, "before")
                    ctx_layout.addWidget(row)

                # Current event highlight
                current_label = QLabel(
                    f"  ▸ {self.event_data.get('title', '')}  "
                    f"({relative_time(self.event_data.get('timestamp', ''))})"
                )
                current_label.setStyleSheet(
                    f"background-color: {COLORS['accent_primary']}33; "
                    f"color: {COLORS['accent_primary']}; "
                    f"border-left: 3px solid {COLORS['accent_primary']}; "
                    f"padding: 6px 10px; border-radius: 4px; font-weight: 600;"
                )
                ctx_layout.addWidget(current_label)

                for evt in context.get("after", []):
                    row = self._make_context_row(evt, "after")
                    ctx_layout.addWidget(row)

                ctx_scroll.setWidget(ctx_widget)
                layout.addWidget(ctx_scroll)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "primary")
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _make_context_row(self, evt, direction):
        """Create a small row for context events."""
        cat_color = category_color(evt.get("category", ""))
        ts = relative_time(evt.get("timestamp", ""))

        label = QLabel(f"  {evt.get('title', '')}  ({ts})")
        label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"border-left: 2px solid {cat_color}; "
            f"padding: 4px 8px; border-radius: 2px;"
        )
        return label


class TimelinePage(QWidget):
    """Timeline page with chronological event list and filters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._current_offset = 0
        self._page_size = 50
        self._setup_ui()

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._auto_refresh_enabled = True
        self._refresh_timer.start(4000)

        QTimer.singleShot(200, self.load_events)

    def _setup_ui(self):
        """Build the timeline page UI."""
        self.setObjectName("timelinePage")
        self.setStyleSheet("""
            QWidget#timelinePage{background:#0b1017}
            QWidget#timelinePage QComboBox,QWidget#timelinePage QDateEdit,QWidget#timelinePage QLineEdit{
                background:#151f2e;border:1px solid #25364e;border-radius:7px;color:#bfd0e6;
                padding:8px 12px;font-size:13px;min-height:26px}
            QWidget#timelinePage QCheckBox{color:#d7e5f5;font-size:13px;background:transparent}
            QWidget#timelinePage QCheckBox::indicator{width:22px;height:22px;border-radius:4px;border:1px solid #7560ed;background:#151f2e}
            QWidget#timelinePage QCheckBox::indicator:checked{background:#7958ef}
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Timeline")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; "
            f"color: {COLORS['text_primary']};"
        )
        header.addWidget(title)
        header.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        header.addWidget(self.auto_refresh_cb)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("background:transparent;border:none;color:#d7e5f5;font-size:13px;padding:6px 12px")
        refresh_btn.clicked.connect(self.load_events)
        header.addWidget(refresh_btn)

        main_layout.addLayout(header)

        # ─── Filter Bar ─────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            f"QFrame {{ background-color: #151e2c; "
            f"border: 1px solid {COLORS['border']}; border-radius: 10px; }}"
        )
        filter_frame.setFixedHeight(86)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        # Category filter
        cat_label = QLabel("Category:")
        cat_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.addItems(
            ["All", "Application", "FileSystem", "System", "Crash"]
        )
        self.category_combo.currentTextChanged.connect(self.load_events)
        filter_layout.addWidget(self.category_combo)

        # Severity filter
        sev_label = QLabel("Severity:")
        sev_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_layout.addWidget(sev_label)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(
            ["All", "info", "warning", "error", "critical"]
        )
        self.severity_combo.currentTextChanged.connect(self.load_events)
        filter_layout.addWidget(self.severity_combo)

        # Date range
        date_label = QLabel("From:")
        date_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_layout.addWidget(date_label)

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        self.date_from.dateChanged.connect(self.load_events)
        filter_layout.addWidget(self.date_from)

        to_label = QLabel("To:")
        to_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_layout.addWidget(to_label)

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        self.date_to.dateChanged.connect(self.load_events)
        filter_layout.addWidget(self.date_to)

        filter_layout.addStretch()

        # Quick filter
        self.quick_search = QLineEdit()
        self.quick_search.setPlaceholderText("Quick filter...")
        self.quick_search.setMaximumWidth(200)
        self.quick_search.textChanged.connect(self._quick_filter_changed)
        filter_layout.addWidget(self.quick_search)

        main_layout.addWidget(filter_frame)

        # ─── Event Count Label ───────────────────────────────────
        self.count_label = QLabel("Loading events...")
        self.count_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        main_layout.addWidget(self.count_label)

        # ─── Event List ──────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: #0b1017; } QScrollBar:vertical{width:6px;background:#101927} QScrollBar::handle:vertical{background:#64759b;min-height:30px;border-radius:3px} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}"
        )

        self.events_widget = QWidget()
        self.events_widget.setStyleSheet("background:#0b1017")
        self.events_layout = QVBoxLayout(self.events_widget)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_layout.setSpacing(8)
        self.events_layout.addStretch()

        self.scroll_area.setWidget(self.events_widget)
        main_layout.addWidget(self.scroll_area, 1)

        # ─── Pagination ─────────────────────────────────────────
        page_layout = QHBoxLayout()
        page_layout.setSpacing(12)

        self.prev_btn = QPushButton("← Newer")
        self.prev_btn.setStyleSheet("background:#0b1017;border:1px solid #25364e;border-radius:8px;padding:10px 18px;color:#bfd0e6;font-size:13px")
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setEnabled(False)
        page_layout.addWidget(self.prev_btn)

        page_layout.addStretch()

        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        page_layout.addWidget(self.page_label)

        page_layout.addStretch()

        self.next_btn = QPushButton("Older →")
        self.next_btn.setStyleSheet(self.prev_btn.styleSheet())
        self.next_btn.clicked.connect(self._next_page)
        page_layout.addWidget(self.next_btn)

        main_layout.addLayout(page_layout)

    @Slot()
    def load_events(self):
        """Load events with current filters."""
        self._current_offset = 0
        self._load_page()

    def _load_page(self):
        """Load a page of events."""
        # Build filters
        category = self.category_combo.currentText()
        if category == "All":
            category = None

        severity = self.severity_combo.currentText()
        if severity == "All":
            severity = None

        start_date = self.date_from.date().toString("yyyy-MM-dd") + "T00:00:00"
        end_date = self.date_to.date().toString("yyyy-MM-dd") + "T23:59:59"

        events = self.db.get_events(
            limit=self._page_size,
            offset=self._current_offset,
            category=category,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
        )

        signature = (events, self.quick_search.text().lower().strip(), self._current_offset)
        if getattr(self, "_rendered_events", None) == signature:
            for card in self.events_widget.findChildren(TimelineEventCard):
                card.refresh_relative_time()
            return
        self._rendered_events = signature

        # Clear existing
        while self.events_layout.count() > 1:
            item = self.events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Quick search filter
        quick_text = self.quick_search.text().lower().strip()

        count = 0
        for event in events:
            if quick_text:
                searchable = (
                    event.get("title", "").lower() +
                    event.get("description", "").lower() +
                    event.get("source", "").lower()
                )
                if quick_text not in searchable:
                    continue

            card = TimelineEventCard(event)
            card.clicked.connect(self._show_event_detail)
            self.events_layout.insertWidget(
                self.events_layout.count() - 1, card
            )
            count += 1

        # Update labels
        page = (self._current_offset // self._page_size) + 1
        self.page_label.setText(f"Page {page}")
        self.count_label.setText(
            f"Showing {count} events"
            + (f" (filtered)" if quick_text else "")
        )

        # Update pagination buttons
        self.prev_btn.setEnabled(self._current_offset > 0)
        self.next_btn.setEnabled(len(events) >= self._page_size)

        # Scroll to top
        self.scroll_area.verticalScrollBar().setValue(0)

    def _prev_page(self):
        self._current_offset = max(
            0, self._current_offset - self._page_size
        )
        self._load_page()

    def _next_page(self):
        self._current_offset += self._page_size
        self._load_page()

    def _quick_filter_changed(self):
        """Re-filter current results without reloading from DB."""
        self._load_page()

    def _toggle_auto_refresh(self, enabled):
        """Toggle auto-refresh."""
        self._auto_refresh_enabled = enabled
        if enabled:
            self._refresh_timer.start(4000)
        else:
            self._refresh_timer.stop()

    def _auto_refresh(self):
        """Auto-refresh if on page 1."""
        if self._auto_refresh_enabled and self._current_offset == 0 and ui_is_presented(self):
            self._load_page()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_refresh_timer") and self._auto_refresh_enabled and self._current_offset == 0:
            self._load_page()

    def _show_event_detail(self, event_data):
        """Show event detail dialog."""
        dialog = EventDetailDialog(event_data, self.db, self)
        dialog.exec()
