"""
LOG NEST - Monitor Manager
Coordinates all monitoring threads and routes events to the database.
"""

import logging
from datetime import datetime
from PySide6.QtCore import QObject, Signal

from src.database import DatabaseManager
from src.monitors.process_monitor import ProcessMonitor
from src.monitors.file_monitor import FileMonitor
from src.monitors.system_event_monitor import SystemEventMonitor

logger = logging.getLogger(__name__)


class MonitorManager(QObject):
    """Manages and coordinates all monitoring threads."""

    new_event = Signal(dict)        # Emitted when any event is stored
    monitor_error = Signal(str)     # Emitted on monitor errors
    status_changed = Signal(str)    # Emitted when monitor status changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._monitors = {}
        self._running = False
        self._event_count = 0

        # Create monitors
        self._init_monitors()

    def _init_monitors(self):
        """Initialize all monitor instances."""
        # Process monitor
        self._monitors["process"] = ProcessMonitor(poll_interval=3.0)
        self._monitors["process"].event_detected.connect(self._on_event)
        self._monitors["process"].error_occurred.connect(self._on_error)

        # File monitor
        self._monitors["file"] = FileMonitor()
        self._monitors["file"].event_detected.connect(self._on_event)
        self._monitors["file"].error_occurred.connect(self._on_error)

        # System event monitor
        self._monitors["system"] = SystemEventMonitor(poll_interval=15.0)
        self._monitors["system"].event_detected.connect(self._on_event)
        self._monitors["system"].error_occurred.connect(self._on_error)

    def start_all(self):
        """Start all monitors."""
        logger.info("Starting all monitors")
        self._running = True

        # Configure file monitor with saved paths
        paths = self.db.get_monitored_paths()
        if paths:
            watch_list = [(p["path"], bool(p["recursive"])) for p in paths]
            self._monitors["file"].set_watched_paths(watch_list)
        else:
            # Default: watch user's Desktop and Documents
            import os
            user_home = os.path.expanduser("~")
            default_paths = []
            for folder in ["Desktop", "Documents", "Downloads"]:
                p = os.path.join(user_home, folder)
                if os.path.isdir(p):
                    default_paths.append((p, False))  # Non-recursive default
                    self.db.add_monitored_path(p, recursive=False)
            self._monitors["file"].set_watched_paths(default_paths)

        # Start each monitor
        for name, monitor in self._monitors.items():
            enabled = self.db.get_setting(f"monitor_{name}_enabled", "true")
            if enabled == "true":
                try:
                    monitor.start()
                    logger.info(f"Started {name} monitor")
                except Exception as e:
                    logger.error(f"Failed to start {name} monitor: {e}")
                    self._on_error(f"Cannot start {name} monitor: {e}")

        self.status_changed.emit("running")

    def stop_all(self):
        """Stop all monitors."""
        logger.info("Stopping all monitors")
        self._running = False

        for name, monitor in self._monitors.items():
            if monitor.isRunning():
                monitor.stop()
                logger.info(f"Stopped {name} monitor")

        self.status_changed.emit("stopped")

    def restart_monitor(self, name):
        """Restart a specific monitor."""
        if name in self._monitors:
            monitor = self._monitors[name]
            if monitor.isRunning():
                monitor.stop()

            # Re-create the monitor
            if name == "process":
                self._monitors[name] = ProcessMonitor(poll_interval=3.0)
            elif name == "file":
                self._monitors[name] = FileMonitor()
                paths = self.db.get_monitored_paths()
                if paths:
                    watch_list = [(p["path"], bool(p["recursive"]))
                                  for p in paths]
                    self._monitors[name].set_watched_paths(watch_list)
            elif name == "system":
                self._monitors[name] = SystemEventMonitor(poll_interval=15.0)

            self._monitors[name].event_detected.connect(self._on_event)
            self._monitors[name].error_occurred.connect(self._on_error)
            self._monitors[name].start()

    def is_monitor_running(self, name):
        """Check if a specific monitor is running."""
        if name in self._monitors:
            return self._monitors[name].isRunning()
        return False

    def _on_event(self, event_data):
        """Handle an event from any monitor."""
        try:
            # Handle in-place event updates (e.g. app session closed updating the open entry)
            if event_data.get("is_update") and event_data.get("id"):
                self.new_event.emit(event_data)
                return

            # Check if event was already pre-inserted by monitor
            if event_data.get("id"):
                self._event_count += 1
                self.new_event.emit(event_data)
                return

            timestamp = event_data.get("timestamp", datetime.now().isoformat())
            event_id = self.db.insert_event(
                event_type=event_data["event_type"],
                category=event_data["category"],
                title=event_data["title"],
                description=event_data.get("description", ""),
                source=event_data.get("source", ""),
                metadata=event_data.get("metadata"),
                severity=event_data.get("severity", "info"),
                timestamp=timestamp,
            )

            event_data["id"] = event_id
            event_data["timestamp"] = timestamp
            self._event_count += 1

            self.new_event.emit(event_data)

        except Exception as e:
            logger.error(f"Error storing event: {e}")

    def _on_error(self, error_msg):
        """Handle monitor errors."""
        logger.error(f"Monitor error: {error_msg}")
        self.monitor_error.emit(error_msg)

    def reload_process_filters(self):
        """Reload application filtering rules for the process monitor."""
        proc_mon = self._monitors.get("process")
        if proc_mon and isinstance(proc_mon, ProcessMonitor):
            proc_mon.reload_filter_settings()

    def get_event_count(self):
        """Get the total number of events detected in this session."""
        return self._event_count

    def get_active_process_count(self):
        """Get the current active process count."""
        proc_mon = self._monitors.get("process")
        if proc_mon and isinstance(proc_mon, ProcessMonitor):
            return proc_mon.get_active_process_count()
        return 0

    def get_active_app_count(self):
        """Get the current active application session count."""
        proc_mon = self._monitors.get("process")
        if proc_mon and isinstance(proc_mon, ProcessMonitor):
            return proc_mon.get_active_app_count()
        return 0

