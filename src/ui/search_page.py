"""
LOG NEST - Search Page
Full-text search with results, context view, and advanced filtering.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QLineEdit,
    QDateEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QDate, Slot
from PySide6.QtGui import QKeySequence, QShortcut

from src.database import DatabaseManager
from src.ui.theme import COLORS, severity_badge_style, category_color
from src.ui.widgets import EventCard
from src.utils.helpers import (
    relative_time, format_timestamp_full, EVENT_TYPE_LABELS
)


class SearchPage(QWidget):
    """Full-text search page with advanced filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._setup_ui()

    def _setup_ui(self):
        """Build the search page UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header
        title = QLabel("Search Events")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; "
            f"color: {COLORS['text_primary']};"
        )
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Search across all events using full-text search. "
            "Find what happened before or after any event."
        )
        subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        subtitle.setWordWrap(True)
        main_layout.addWidget(subtitle)

        # ─── Search Bar ──────────────────────────────────────────
        search_frame = QFrame()
        search_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(20, 20, 20, 20)
        search_layout.setSpacing(12)

        # Main search input
        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "🔍  Search events... (e.g., 'chrome crash', 'document modified')"
        )
        self.search_input.setStyleSheet(
            f"QLineEdit {{ font-size: 16px; padding: 14px 18px; "
            f"border-radius: 10px; }}"
        )
        self.search_input.returnPressed.connect(self._do_search)
        input_row.addWidget(self.search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.setProperty("class", "primary")
        search_btn.setStyleSheet(
            f"QPushButton {{ font-size: 14px; padding: 14px 28px; "
            f"background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 10px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: #7B73FF; }}"
        )
        search_btn.clicked.connect(self._do_search)
        input_row.addWidget(search_btn)

        search_layout.addLayout(input_row)

        # Advanced filters row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        cat_label = QLabel("Category:")
        cat_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_row.addWidget(cat_label)

        self.search_category = QComboBox()
        self.search_category.addItems(
            ["All", "Application", "FileSystem", "System", "Crash"]
        )
        filter_row.addWidget(self.search_category)

        date_label = QLabel("Date range:")
        date_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; "
            f"font-weight: 600; border: none;"
        )
        filter_row.addWidget(date_label)

        self.search_date_from = QDateEdit()
        self.search_date_from.setDate(QDate.currentDate().addDays(-30))
        self.search_date_from.setCalendarPopup(True)
        filter_row.addWidget(self.search_date_from)

        to_label = QLabel("to")
        to_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; border: none;"
        )
        filter_row.addWidget(to_label)

        self.search_date_to = QDateEdit()
        self.search_date_to.setDate(QDate.currentDate())
        self.search_date_to.setCalendarPopup(True)
        filter_row.addWidget(self.search_date_to)

        filter_row.addStretch()
        search_layout.addLayout(filter_row)

        main_layout.addWidget(search_frame)

        # ─── Results ─────────────────────────────────────────────
        self.results_label = QLabel("")
        self.results_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        main_layout.addWidget(self.results_label)

        # Results scroll area
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        self.results_layout.addStretch()

        # Empty state
        self.empty_label = QLabel(
            "🔍\n\nEnter a search term to find events.\n"
            "You can search by application name, file path, error message, or any text."
        )
        self.empty_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 14px;"
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.results_layout.insertWidget(0, self.empty_label)

        self.results_scroll.setWidget(self.results_widget)
        main_layout.addWidget(self.results_scroll, 1)

    @Slot()
    def _do_search(self):
        """Execute the search."""
        query = self.search_input.text().strip()
        if not query:
            return

        category = self.search_category.currentText()
        if category == "All":
            category = None

        start_date = (
            self.search_date_from.date().toString("yyyy-MM-dd") + "T00:00:00"
        )
        end_date = (
            self.search_date_to.date().toString("yyyy-MM-dd") + "T23:59:59"
        )

        try:
            results = self.db.search_events(
                query, limit=50, category=category,
                start_date=start_date, end_date=end_date
            )
        except Exception as e:
            self.results_label.setText(f"Search error: {e}")
            return

        # Clear previous results
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Remove empty label if present
        self.empty_label.setVisible(False)

        if not results:
            no_results = QLabel(
                f"No results found for \"{query}\"\n\n"
                "Try different keywords or broaden your date range."
            )
            no_results.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 14px;"
            )
            no_results.setAlignment(Qt.AlignCenter)
            self.results_layout.insertWidget(0, no_results)
            self.results_label.setText("0 results")
            return

        self.results_label.setText(
            f"Found {len(results)} result{'s' if len(results) != 1 else ''} "
            f"for \"{query}\""
        )

        for event in results:
            card = SearchResultCard(event, query)
            self.results_layout.insertWidget(
                self.results_layout.count() - 1, card
            )

    def focus_search(self):
        """Focus the search input."""
        self.search_input.setFocus()
        self.search_input.selectAll()


class SearchResultCard(QFrame):
    """Enhanced event card for search results with context snippet."""

    def __init__(self, event_data, query="", parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.query = query
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(90)
        self._setup_ui()

    def _setup_ui(self):
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

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Title with highlighted matches
        title = self.event_data.get("title", "")
        title_html = self._highlight_query(title)
        title_label = QLabel(title_html)
        title_label.setTextFormat(Qt.RichText)
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; "
            f"background: transparent; border: none;"
        )
        title_label.setWordWrap(True)
        content_layout.addWidget(title_label)

        # Description with highlighted matches
        desc = self.event_data.get("description", "")
        if desc:
            desc_short = desc[:200]
            desc_html = self._highlight_query(desc_short)
            desc_label = QLabel(desc_html)
            desc_label.setTextFormat(Qt.RichText)
            desc_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 12px; "
                f"background: transparent; border: none;"
            )
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)

        # Bottom row
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        cat_label = QLabel(f"● {cat}")
        cat_label.setStyleSheet(
            f"color: {cat_color}; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        bottom.addWidget(cat_label)

        type_label = QLabel(
            EVENT_TYPE_LABELS.get(
                self.event_data.get("event_type", ""),
                self.event_data.get("event_type", "")
            )
        )
        type_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        bottom.addWidget(type_label)

        bottom.addStretch()

        ts = relative_time(self.event_data.get("timestamp", ""))
        time_label = QLabel(f"🕐 {ts}")
        time_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        bottom.addWidget(time_label)

        content_layout.addLayout(bottom)
        layout.addLayout(content_layout, 1)

    def _highlight_query(self, text):
        """Highlight the search query in text using HTML."""
        if not self.query or not text:
            return text
        import re
        # Escape HTML special characters in text first
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Case-insensitive highlight
        pattern = re.escape(self.query)
        highlighted = re.sub(
            f"({pattern})",
            f'<span style="background-color: {COLORS["accent_primary"]}44; '
            f'color: {COLORS["accent_primary"]}; font-weight: 600;">\\1</span>',
            text,
            flags=re.IGNORECASE
        )
        return highlighted

    def enterEvent(self, event):
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_hover']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 12px; }}"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("")
        super().leaveEvent(event)
