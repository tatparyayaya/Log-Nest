"""
Unit and Integration Tests for LOG NEST Digital Wellbeing & Real-Time Sync.
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.database import DatabaseManager
from src.monitors.screen_time_monitor import ScreenTimeMonitor, get_system_idle_seconds
from src.ui.wellbeing_widgets import WellbeingRingChart, LiveActiveAppCard, AppUsageRowWidget, DailyLimitDialog, FocusModeWidget, HourlyScreenTimeChart
from src.ui.digital_wellbeing_page import DigitalWellbeingPage
from src.ui.dashboard_page import DashboardPage
from src.ui.main_window import MainWindow
from src.utils.helpers import format_screen_time


def test_screen_time_helpers():
    print("Testing Screen Time Helpers...")
    assert format_screen_time(0) == "0 min"
    assert format_screen_time(45) == "< 1 min"
    assert format_screen_time(45, detailed=True) == "45 sec"
    assert format_screen_time(120) == "2 min"
    assert format_screen_time(3600) == "1 hr"
    assert format_screen_time(3660) == "1 hr 1 min"
    assert format_screen_time(7200) == "2 hr"
    print("  Screen time formatting verified.")


def test_database_digital_wellbeing():
    print("Testing Database Digital Wellbeing Methods...")
    db = DatabaseManager()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Record screen time
    db.record_screen_time("test_chrome", "Google Chrome", "Browser", 125.0, date_str=today_str, hour=14)
    db.record_screen_time("test_code", "VS Code", "Developer Tool", 300.0, date_str=today_str, hour=14)
    db.record_screen_time("test_code", "VS Code", "Developer Tool", 60.0, date_str=today_str, hour=15)
    db.increment_app_launches("test_chrome", "Google Chrome", "Browser", date_str=today_str)

    # 2. Get daily summary
    summary = db.get_daily_screen_time(date_str=today_str)
    assert summary is not None
    assert summary["total_seconds"] >= 485.0
    assert any(a["app_id"] == "test_code" for a in summary["apps"])
    assert any(a["app_id"] == "test_chrome" for a in summary["apps"])
    print(f"  Recorded and verified daily screen time: {summary['total_seconds']}s across {len(summary['apps'])} apps")

    # 3. Hourly screen time
    hourly = db.get_hourly_screen_time(date_str=today_str)
    assert hourly[14] >= 425.0
    assert hourly[15] >= 60.0
    print(f"  Hourly distribution verified (Hour 14: {hourly[14]}s, Hour 15: {hourly[15]}s)")

    # 4. App Limits
    db.set_app_limit("test_chrome", "Google Chrome", 45, enabled=1)
    limits = db.get_app_limits()
    assert any(l["app_id"] == "test_chrome" and l["daily_limit_minutes"] == 45 for l in limits)

    chrome_limit = db.get_app_limit("test_chrome")
    assert chrome_limit["daily_limit_minutes"] == 45

    db.remove_app_limit("test_chrome")
    assert db.get_app_limit("test_chrome") is None
    print("  App limit lifecycle (set, fetch, remove) verified.")


def test_screen_time_monitor():
    print("Testing Screen Time Monitor...")
    db = DatabaseManager()
    monitor = ScreenTimeMonitor(idle_timeout=120.0)

    # Test idle calculation function
    idle_sec = get_system_idle_seconds()
    assert isinstance(idle_sec, float)
    assert idle_sec >= 0.0

    # Test pending flush
    monitor._current_app_id = "test_spotify"
    monitor._current_app_name = "Spotify"
    monitor._current_category = "Media"
    monitor._pending_accumulated_seconds = 15.0
    monitor.flush_pending()

    summary = db.get_daily_screen_time()
    assert any(a["app_id"] == "test_spotify" for a in summary["apps"])
    print("  Screen time monitor flush and state verified.")


def test_wellbeing_ui():
    print("Testing Digital Wellbeing UI Integration...")
    app = QApplication.instance() or QApplication(sys.argv)

    # Test widgets
    ring = WellbeingRingChart()
    ring.set_data(3600.0, [{"app_id": "code", "app_name": "VS Code", "duration_seconds": 3600.0}])
    assert ring._center_title == "1 hr"

    live_card = LiveActiveAppCard()
    live_card.update_tick({
        "app_id": "test_app",
        "app_name": "Test Application",
        "category": "Developer Tool",
        "is_idle": False,
        "session_seconds": 125,
        "app_today_seconds": 500,
        "today_total_seconds": 1500,
        "pc_time_str": "04:30:00 PM",
        "pc_date_str": "Monday, Oct 19, 2026",
    })
    assert live_card.app_title.text() == "Test Application"

    hourly_chart = HourlyScreenTimeChart()
    hourly_chart.set_data({14: 1200.0, 15: 800.0})

    focus_widget = FocusModeWidget()
    assert focus_widget._focus_remaining_seconds == 25 * 60

    # Test Wellbeing Page
    wb_page = DigitalWellbeingPage()
    assert wb_page is not None

    # Test Dashboard Page integration
    db_page = DashboardPage()
    assert hasattr(db_page, "wellbeing_page")
    assert hasattr(db_page, "btn_tab_wellbeing")
    assert hasattr(db_page, "btn_tab_activity")
    assert hasattr(db_page, "stat_total")  # older attributes intact!

    # Switch to system activity and back
    db_page._switch_view(1)
    assert db_page._current_view_idx == 1
    db_page._switch_view(0)
    assert db_page._current_view_idx == 0

    # Test MainWindow
    win = MainWindow()
    assert len(win._nav_buttons) == 4
    assert win._page_stack.count() == 4
    assert hasattr(win, "_pc_clock_label")

    win._quit_app()
    app.processEvents()
    print("  Digital Wellbeing UI instantiation and backward compatibility verified.")


if __name__ == "__main__":
    test_screen_time_helpers()
    test_database_digital_wellbeing()
    test_screen_time_monitor()
    test_wellbeing_ui()
    print("\nALL DIGITAL WELLBEING AND REAL-TIME SYNC TESTS PASSED!")
    sys.exit(0)
