"""
LOG NEST - Main Window
Primary application window with sidebar navigation and system tray support.
"""

import os
import sys
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSystemTrayIcon, QMenu, QStatusBar, QApplication,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Slot, QSize
from PySide6.QtGui import QIcon, QAction, QFont, QPixmap, QPainter, QColor

from src.ui.theme import COLORS, get_main_stylesheet
from src.ui.dashboard_page import DashboardPage
from src.ui.timeline_page import TimelinePage
from src.ui.search_page import SearchPage
from src.ui.settings_page import SettingsPage
from src.ui.widgets import PulsingDot
from src.monitors.monitor_manager import MonitorManager

logger = logging.getLogger(__name__)


def _get_app_icon():
    """Load application icon from file or fallback to generated icon."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for path in [
        os.path.join(base_dir, "app_icon.ico"),
        os.path.join(base_dir, "app_icon.png"),
        "app_icon.ico",
        "app_icon.png",
    ]:
        if os.path.exists(path):
            return QIcon(path)
    return QIcon(_create_colored_icon())


def _create_colored_icon(color_hex="#2563EB", size=64):
    """Create a simple colored icon pixmap for the app fallback."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer circle
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color_hex))
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 14, 14)

    # Inner "L" letter
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("white"))
    font = QFont("Segoe UI", int(size * 0.4), QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "L")

    painter.end()
    return pixmap


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LOG NEST — Activity Tracker")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # App icon
        self._app_icon = _get_app_icon()
        self.setWindowIcon(self._app_icon)
        self._apply_native_windows_icon()

        # Apply theme
        self.setStyleSheet(get_main_stylesheet())

        # Monitor manager
        self.monitor_manager = MonitorManager()
        self.monitor_manager.new_event.connect(self._on_new_event)
        self.monitor_manager.monitor_error.connect(self._on_monitor_error)

        # Build UI
        self._setup_ui()
        self._setup_tray()
        self._setup_statusbar()

        # Connect Screen Time & Digital Wellbeing signals
        self.monitor_manager.active_screen_tick.connect(self._dashboard.on_active_tick)
        self.monitor_manager.daily_limit_reached.connect(self._on_daily_limit_reached)

        # Start monitoring
        self._start_monitors_timer = QTimer(self)
        self._start_monitors_timer.setSingleShot(True)
        self._start_monitors_timer.timeout.connect(self._start_monitors)
        self._start_monitors_timer.start(500)

    def _apply_native_windows_icon(self):
        """Ensure the native Windows window and taskbar icons use exact system metric resolutions."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ico_path = os.path.join(base_dir, "app_icon.ico")
            if not os.path.exists(ico_path):
                ico_path = "app_icon.ico"
            if not os.path.exists(ico_path):
                return

            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            LR_LOADFROMFILE = 0x00000010
            IMAGE_ICON = 1
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1

            cx_sm = user32.GetSystemMetrics(49)  # SM_CXSMICON
            cy_sm = user32.GetSystemMetrics(50)  # SM_CYSMICON
            cx_lg = user32.GetSystemMetrics(11)  # SM_CXICON
            cy_lg = user32.GetSystemMetrics(12)  # SM_CYICON

            h_small = user32.LoadImageW(None, os.path.abspath(ico_path), IMAGE_ICON, cx_sm, cy_sm, LR_LOADFROMFILE)
            h_big = user32.LoadImageW(None, os.path.abspath(ico_path), IMAGE_ICON, cx_lg, cy_lg, LR_LOADFROMFILE)

            if h_small:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
            if h_big:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
        except Exception as e:
            logger.debug(f"Could not apply native Windows icon: {e}")

    def _setup_ui(self):
        """Build the main window UI with sidebar navigation."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─── Sidebar ────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo / Title Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(14, 14, 14, 12)
        header_layout.setSpacing(10)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(base_dir, "app_icon.png")
        if not os.path.exists(logo_path):
            logo_path = "app_icon.png"

        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_pix = QPixmap(logo_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pix)
            logo_label.setFixedSize(40, 40)
            logo_label.setStyleSheet("border: none; background: transparent;")
            header_layout.addWidget(logo_label)

        title_vbox = QVBoxLayout()
        title_vbox.setContentsMargins(0, 0, 0, 0)
        title_vbox.setSpacing(1)

        title_label = QLabel("LOG NEST")
        title_label.setObjectName("sidebarTitle")
        title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"letter-spacing: 0.6px; border: none; background: transparent;"
        )
        title_vbox.addWidget(title_label)

        subtitle = QLabel("Activity Tracker")
        subtitle.setObjectName("sidebarSubtitle")
        subtitle.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 500; "
            f"border: none; background: transparent;"
        )
        title_vbox.addWidget(subtitle)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        sidebar_layout.addWidget(header_widget)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(
            f"background-color: {COLORS['border']}; max-height: 1px; "
            f"margin: 0 12px;"
        )
        sidebar_layout.addWidget(sep)

        sidebar_layout.addSpacing(8)

        # Navigation buttons
        self._nav_buttons = []
        nav_items = [
            ("📊  Dashboard", 0),
            ("📋  Timeline", 1),
            ("🔍  Search", 2),
            ("⚙️  Settings", 3),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "nav-button")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Status indicator at bottom of sidebar
        status_frame = QFrame()
        status_frame.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; "
            f"border-top: 1px solid {COLORS['border']}; border-radius: 0;"
        )
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(6)

        self._status_dot = PulsingDot(COLORS["accent_secondary"], size=7)
        status_layout.addWidget(self._status_dot)

        self._status_label = QLabel("Monitoring active")
        self._status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"font-weight: 500; border: none;"
        )
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()

        sidebar_layout.addWidget(status_frame)
        main_layout.addWidget(sidebar)

        # ─── Content Area ────────────────────────────────────────
        self._page_stack = QStackedWidget()
        self._page_stack.setStyleSheet("background-color: transparent;")

        # Create pages
        self._dashboard = DashboardPage()
        self._timeline = TimelinePage()
        self._search = SearchPage()
        self._settings = SettingsPage()

        # Connect settings signals
        self._settings.monitors_changed.connect(self._on_settings_changed)
        self._settings.paths_changed.connect(self._on_paths_changed)

        self._page_stack.addWidget(self._dashboard)
        self._page_stack.addWidget(self._timeline)
        self._page_stack.addWidget(self._search)
        self._page_stack.addWidget(self._settings)

        main_layout.addWidget(self._page_stack, 1)

        # Set initial page
        self._switch_page(0)

    def _setup_tray(self):
        """Setup system tray icon and menu."""
        self._tray = QSystemTrayIcon(self._app_icon, self)

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            f"QMenu {{ background-color: {COLORS['bg_medium']}; "
            f"color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; padding: 4px; }}"
            f"QMenu::item {{ padding: 8px 20px; border-radius: 4px; }}"
            f"QMenu::item:selected {{ background-color: {COLORS['accent_primary']}; "
            f"color: white; }}"
        )

        show_action = QAction("Show LOG NEST", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _setup_statusbar(self):
        """Setup the status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._event_counter_label = QLabel("Events: 0")
        self._event_counter_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; padding: 0 8px;"
        )
        self._statusbar.addPermanentWidget(self._event_counter_label)

        # Real-time PC Clock in status bar
        now_dt = datetime.now()
        self._pc_clock_label = QLabel(f"🕒 {now_dt.strftime('%I:%M:%S %p')}  •  {now_dt.strftime('%b %d')}")
        self._pc_clock_label.setStyleSheet(
            f"color: {COLORS['accent_secondary']}; font-weight: 600; font-size: 11px; padding: 0 12px;"
        )
        self._statusbar.addPermanentWidget(self._pc_clock_label)

        # Update counter and clock periodically
        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)
        self._counter_timer.start(1000)

    def _update_clock(self):
        """Update PC real-time clock label in statusbar."""
        now_dt = datetime.now()
        self._pc_clock_label.setText(f"🕒 {now_dt.strftime('%I:%M:%S %p')}  •  {now_dt.strftime('%b %d')}")

    def _switch_page(self, index):
        """Switch to a page by index."""
        self._page_stack.setCurrentIndex(index)

        # Update nav button states
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Focus search input if switching to search page
        if index == 2:
            self._search.focus_search()

    @Slot()
    def _start_monitors(self):
        """Start all monitors."""
        self.monitor_manager.start_all()
        self._status_label.setText("Monitoring active")
        self._statusbar.showMessage("All monitors started", 3000)

    @Slot(dict)
    def _on_new_event(self, event_data):
        """Handle new event from monitors."""
        # Update dashboard live
        self._dashboard.add_live_event(event_data)

        # Show tray notification for errors/crashes
        severity = event_data.get("severity", "info")
        if severity in ("error", "critical"):
            self._tray.showMessage(
                "LOG NEST — " + severity.upper(),
                event_data.get("title", "Event detected"),
                QSystemTrayIcon.Warning,
                3000
            )

    @Slot(str)
    def _on_monitor_error(self, error_msg):
        """Handle monitor errors."""
        self._statusbar.showMessage(f"Monitor error: {error_msg}", 5000)
        logger.error(f"Monitor error: {error_msg}")

    @Slot()
    def _on_settings_changed(self):
        """Handle settings changes."""
        self.monitor_manager.reload_process_filters()
        self._statusbar.showMessage("Settings updated", 3000)


    @Slot()
    def _on_paths_changed(self):
        """Handle monitored paths changes."""
        self.monitor_manager.restart_monitor("file")
        self._statusbar.showMessage("File monitor restarted", 3000)

    def _update_counter(self):
        """Update the event counter and PC clock in the status bar."""
        count = self.monitor_manager.get_event_count()
        self._event_counter_label.setText(f"Session events: {count}")
        self._update_clock()

    @Slot(dict)
    def _on_daily_limit_reached(self, limit_data):
        """Show tray notification and alert when an app reaches its daily screen time limit."""
        app_name = limit_data.get("app_name", "Application")
        formatted_limit = limit_data.get("formatted_limit", "")
        formatted_used = limit_data.get("formatted_used", "")
        self._tray.showMessage(
            "Digital Wellbeing — Daily Limit Reached",
            f"{app_name} reached your limit of {formatted_limit} (Used: {formatted_used}).",
            QSystemTrayIcon.Warning,
            6000
        )
        self._statusbar.showMessage(f"⚠️ Digital Wellbeing: Daily limit reached for {app_name} ({formatted_limit})", 6000)

    def _tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        """Show the window from system tray."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self):
        """Quit the application cleanly."""
        if hasattr(self, "_start_monitors_timer") and self._start_monitors_timer.isActive():
            self._start_monitors_timer.stop()
        if hasattr(self, "_counter_timer") and self._counter_timer.isActive():
            self._counter_timer.stop()
        self.monitor_manager.stop_all()
        if hasattr(self, "_tray") and self._tray:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
        QApplication.instance().quit()



    def closeEvent(self, event):
        """Minimize to tray on close instead of quitting."""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "LOG NEST",
            "Running in background. Double-click tray icon to open.",
            QSystemTrayIcon.Information,
            2000
        )
