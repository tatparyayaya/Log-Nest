"""
LOG NEST - Screen Time Monitor (Digital Wellbeing)
Tracks active foreground application usage in real time, synchronizes with the
PC's system clock, calculates exact screen time, detects idle time, and monitors daily app limits.
"""

import time
import logging
import ctypes
import ctypes.wintypes
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtCore import QThread, Signal
import psutil

from src.database import DatabaseManager
from src.utils.app_metadata import resolve_application_info, resolve_window_pid, AppInfo
from src.utils.helpers import format_screen_time

logger = logging.getLogger(__name__)


def get_system_idle_seconds() -> float:
    """Get the number of seconds since last user keyboard or mouse input."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            current_tick = ctypes.windll.kernel32.GetTickCount()
            elapsed_ms = current_tick - lii.dwTime
            return max(elapsed_ms / 1000.0, 0.0)
    except Exception as e:
        logger.debug(f"Error checking last input info: {e}")
    return 0.0


class ScreenTimeMonitor(QThread):
    """
    Background thread tracking active foreground application screen time.
    Synchronizes with PC real-time clock and supports Android-style Digital Wellbeing tracking.
    """

    active_tick = Signal(dict)          # Emitted every second with active foreground data
    daily_limit_reached = Signal(dict)  # Emitted when an app crosses its daily limit
    day_rolled_over = Signal(str)       # Emitted when midnight passes to a new day
    error_occurred = Signal(str)

    def __init__(self, idle_timeout: float = 120.0, parent=None):
        super().__init__(parent)
        self.idle_timeout = idle_timeout
        self._running = False
        self.db = DatabaseManager()

        # State tracking
        self._current_app_id: Optional[str] = None
        self._current_app_name: str = "Desktop"
        self._current_category: str = "System"
        self._current_session_seconds: float = 0.0
        self._pending_accumulated_seconds: float = 0.0
        self._current_date: str = datetime.now().strftime("%Y-%m-%d")
        self._notified_limits_today: set = set()
        self._is_idle: bool = False

    def run(self):
        """Main real-time tracking loop (ticking once per second)."""
        self._running = True
        logger.info("Screen Time Monitor started (Real-Time Digital Wellbeing)")

        last_flush_time = time.time()

        while self._running:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # Handle date rollover at midnight
                if today_str != self._current_date:
                    self.flush_pending()
                    self._current_date = today_str
                    self._notified_limits_today.clear()
                    self.day_rolled_over.emit(today_str)

                # Check user idle status
                idle_sec = get_system_idle_seconds()
                is_idle = idle_sec >= self.idle_timeout
                self._is_idle = is_idle

                active_app_info = None
                if not is_idle:
                    active_app_info = self._get_foreground_app()

                if is_idle or not active_app_info:
                    # User is idle or locked
                    if self._pending_accumulated_seconds > 0:
                        self.flush_pending()
                else:
                    app_id = active_app_info["app_id"]
                    app_name = active_app_info["app_name"]
                    category = active_app_info["category"]

                    if app_id != self._current_app_id:
                        # Foreground window switched to another application
                        self.flush_pending()
                        self._current_app_id = app_id
                        self._current_app_name = app_name
                        self._current_category = category
                        self._current_session_seconds = 0.0

                        # Increment app launch count for today
                        try:
                            self.db.increment_app_launches(app_id, app_name, category, self._current_date)
                        except Exception as e:
                            logger.debug(f"Could not increment launches: {e}")

                    # Accumulate 1 second of active screen time
                    self._current_session_seconds += 1.0
                    self._pending_accumulated_seconds += 1.0

                    # Flush to database periodically (every 5 seconds)
                    if time.time() - last_flush_time >= 5.0:
                        self.flush_pending()
                        last_flush_time = time.time()

                    # Check daily limit alert
                    self._check_daily_limit(app_id, app_name)

                # Fetch today's summary to include in tick
                today_summary = None
                try:
                    today_summary = self.db.get_daily_screen_time(self._current_date)
                except Exception:
                    pass

                today_total_sec = today_summary["total_seconds"] if today_summary else 0.0
                app_today_sec = 0.0
                if today_summary and self._current_app_id:
                    for app in today_summary.get("apps", []):
                        if app["app_id"] == self._current_app_id:
                            app_today_sec = app["duration_seconds"]
                            break

                # Emit active tick signal
                tick_data = {
                    "app_id": self._current_app_id or "idle",
                    "app_name": self._current_app_name if not is_idle else "Idle / Screen Paused",
                    "category": self._current_category if not is_idle else "Idle",
                    "is_idle": is_idle,
                    "session_seconds": self._current_session_seconds if not is_idle else 0.0,
                    "app_today_seconds": app_today_sec,
                    "today_total_seconds": today_total_sec,
                    "pc_time_str": now.strftime("%I:%M:%S %p"),
                    "pc_date_str": now.strftime("%A, %B %d, %Y"),
                    "date_iso": today_str,
                }
                self.active_tick.emit(tick_data)

            except Exception as e:
                logger.error(f"Error in ScreenTimeMonitor: {e}", exc_info=True)
                self.error_occurred.emit(str(e))

            # Sleep 1 second for precise real-time synchronization
            time.sleep(1.0)

        # On stopping, flush any remaining time
        self.flush_pending()
        logger.info("Screen Time Monitor stopped")

    def _get_foreground_app(self) -> Optional[Dict[str, Any]]:
        """Retrieve application identity of current foreground window."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            pid = resolve_window_pid(hwnd)
            if pid <= 4:
                return None

            proc = psutil.Process(pid)
            name = proc.name()
            exe = ""
            try:
                exe = proc.exe()
            except Exception:
                pass

            cmdline = []
            try:
                cmdline = proc.cmdline()
            except Exception:
                pass

            app_info: AppInfo = resolve_application_info(name, exe, cmdline)
            return {
                "app_id": app_info.app_id,
                "app_name": app_info.display_name,
                "category": app_info.category,
                "pid": pid,
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
        except Exception as e:
            logger.debug(f"Error resolving foreground window: {e}")
            return None

    def flush_pending(self):
        """Flush pending screen time seconds to SQLite database."""
        if self._current_app_id and self._pending_accumulated_seconds > 0:
            try:
                self.db.record_screen_time(
                    app_id=self._current_app_id,
                    app_name=self._current_app_name,
                    category=self._current_category,
                    seconds=self._pending_accumulated_seconds,
                    date_str=self._current_date,
                    hour=datetime.now().hour,
                )
                self._pending_accumulated_seconds = 0.0
            except Exception as e:
                logger.warning(f"Failed to flush screen time to DB: {e}")

    def _check_daily_limit(self, app_id: str, app_name: str):
        """Check if an app has crossed its daily usage limit."""
        if app_id in self._notified_limits_today:
            return

        try:
            limit_entry = self.db.get_app_limit(app_id)
            if limit_entry and limit_entry.get("enabled"):
                limit_mins = limit_entry["daily_limit_minutes"]
                limit_seconds = limit_mins * 60.0

                summary = self.db.get_daily_screen_time(self._current_date)
                for app in summary.get("apps", []):
                    if app["app_id"] == app_id:
                        total_secs = app["duration_seconds"] + self._pending_accumulated_seconds
                        if total_secs >= limit_seconds:
                            self._notified_limits_today.add(app_id)
                            self.daily_limit_reached.emit({
                                "app_id": app_id,
                                "app_name": app_name,
                                "limit_minutes": limit_mins,
                                "used_seconds": total_secs,
                                "formatted_limit": f"{limit_mins} min",
                                "formatted_used": format_screen_time(total_secs),
                            })
                        break
        except Exception as e:
            logger.debug(f"Error checking app limit: {e}")

    def stop(self):
        """Stop monitor thread cleanly."""
        self._running = False
        self.wait(3000)
