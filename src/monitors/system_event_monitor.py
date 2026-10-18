"""
LOG NEST - Windows System Event Monitor
Reads Windows Event Log entries (Application, System) for errors,
warnings, and crash reports.
"""

import time
import logging
from datetime import datetime, timedelta
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

try:
    import win32evtlog
    import win32evtlogutil
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not available — system event monitoring disabled")


# Event log types to human-readable severity
EVENT_TYPE_MAP = {
    1: ("error", "Error"),          # EVENTLOG_ERROR_TYPE
    2: ("warning", "Warning"),      # EVENTLOG_WARNING_TYPE
    4: ("info", "Information"),     # EVENTLOG_INFORMATION_TYPE
    8: ("info", "Audit Success"),   # EVENTLOG_AUDIT_SUCCESS
    16: ("warning", "Audit Failure"),  # EVENTLOG_AUDIT_FAILURE
}

# Known crash event sources
CRASH_SOURCES = {
    "Application Error",
    "Application Hang",
    "Windows Error Reporting",
    ".NET Runtime",
    "Application Crash",
}


class SystemEventMonitor(QThread):
    """Background thread that reads Windows Event Log."""

    event_detected = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, poll_interval=15.0, parent=None):
        super().__init__(parent)
        self.poll_interval = poll_interval
        self._running = False
        self._last_read_times = {}  # log_name -> last timestamp
        self._seen_record_ids = {}  # log_name -> set of record numbers

    def run(self):
        """Main monitoring loop."""
        if not HAS_WIN32:
            logger.warning("System event monitor cannot start: pywin32 missing")
            self.error_occurred.emit(
                "pywin32 is required for system event monitoring")
            return

        self._running = True
        logger.info("System event monitor started")

        # Initialize with current time to avoid reading old events
        now = datetime.now()
        for log_name in ("Application", "System"):
            self._last_read_times[log_name] = now - timedelta(seconds=30)
            self._seen_record_ids[log_name] = set()

        while self._running:
            try:
                for log_name in ("Application", "System"):
                    self._read_events(log_name)
            except Exception as e:
                logger.error(f"System event monitor error: {e}")
                self.error_occurred.emit(str(e))
            time.sleep(self.poll_interval)

        logger.info("System event monitor stopped")

    def _read_events(self, log_name):
        """Read recent events from a Windows Event Log."""
        server = None  # Local machine
        flags = (win32evtlog.EVENTLOG_BACKWARDS_READ |
                 win32evtlog.EVENTLOG_SEQUENTIAL_READ)

        try:
            handle = win32evtlog.OpenEventLog(server, log_name)
        except Exception as e:
            logger.error(f"Cannot open event log '{log_name}': {e}")
            return

        try:
            total = win32evtlog.GetNumberOfEventLogRecords(handle)
            if total == 0:
                return

            events_read = 0
            max_events = 50  # Max events per poll cycle

            while events_read < max_events:
                events = win32evtlog.ReadEventLog(handle, flags, 0)
                if not events:
                    break

                for event in events:
                    events_read += 1

                    # Check if we've already processed this event
                    record_num = event.RecordNumber
                    if record_num in self._seen_record_ids.get(log_name, set()):
                        continue

                    # Check if event is recent enough
                    event_time = event.TimeGenerated
                    if hasattr(event_time, 'timestamp'):
                        event_dt = datetime.fromtimestamp(
                            event_time.timestamp())
                    else:
                        # pywintypes.datetime
                        event_dt = datetime(
                            event_time.year, event_time.month,
                            event_time.day, event_time.hour,
                            event_time.minute, event_time.second)

                    if event_dt < self._last_read_times[log_name]:
                        return  # We've gone past our window

                    # Only process errors and warnings
                    event_type_id = event.EventType
                    if event_type_id not in (1, 2):  # Error, Warning only
                        continue

                    # Track seen events
                    if log_name not in self._seen_record_ids:
                        self._seen_record_ids[log_name] = set()
                    self._seen_record_ids[log_name].add(record_num)

                    # Limit tracked IDs to prevent memory growth
                    if len(self._seen_record_ids[log_name]) > 5000:
                        seen = sorted(self._seen_record_ids[log_name])
                        self._seen_record_ids[log_name] = set(seen[-2500:])

                    self._process_event(event, log_name, event_dt)

        except Exception as e:
            logger.error(f"Error reading {log_name} log: {e}")
        finally:
            win32evtlog.CloseEventLog(handle)

        self._last_read_times[log_name] = datetime.now()

    def _process_event(self, event, log_name, event_dt):
        """Process a single Windows Event Log entry."""
        source_name = event.SourceName or "Unknown"
        event_type_id = event.EventType
        severity_info = EVENT_TYPE_MAP.get(event_type_id, ("info", "Info"))
        severity = severity_info[0]
        type_label = severity_info[1]

        # Try to get event message
        try:
            message = win32evtlogutil.SafeFormatMessage(event, log_name)
            if message:
                message = message.strip()[:500]  # Limit length
            else:
                message = f"Event ID: {event.EventID & 0xFFFF}"
        except Exception:
            message = f"Event ID: {event.EventID & 0xFFFF}"

        # Determine if this is a crash event
        is_crash = source_name in CRASH_SOURCES
        if is_crash:
            event_type = "crash"
            category = "Crash"
            severity = "critical"
        elif event_type_id == 1:
            event_type = "system_error"
            category = "System"
        elif event_type_id == 2:
            event_type = "system_warning"
            category = "System"
        else:
            event_type = "system_event"
            category = "System"

        title = f"[{log_name}] {source_name}: {type_label}"
        if is_crash:
            title = f"💥 Crash: {source_name}"

        evt = {
            "event_type": event_type,
            "category": category,
            "source": source_name,
            "title": title,
            "description": message,
            "severity": severity,
            "timestamp": event_dt.isoformat(),
            "metadata": {
                "log_name": log_name,
                "event_id": event.EventID & 0xFFFF,
                "record_number": event.RecordNumber,
                "event_category": event.EventCategory,
                "type_label": type_label,
            },
        }

        self.event_detected.emit(evt)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        self.wait(5000)
