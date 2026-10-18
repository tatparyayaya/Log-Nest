"""
LOG NEST - File System Monitor
Watches configured directories for file changes using the watchdog library.
"""

import os
import time
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtCore import QThread, Signal, QMutex

logger = logging.getLogger(__name__)

# Extensions to ignore
IGNORED_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".lock", ".swp", ".swo",
    ".pyc", ".pyo", ".crdownload", ".part",
    ".db-journal", ".db-wal", ".db-shm",
}

# Directories to ignore
IGNORED_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules",
    ".vs", ".idea", ".vscode", "AppData", "$Recycle.Bin",
    "System Volume Information", ".lognest",
}


class LogNestEventHandler(FileSystemEventHandler):
    """Custom file system event handler that emits Qt signals."""

    def __init__(self, signal_emitter, debounce_seconds=1.0):
        super().__init__()
        self._signal = signal_emitter
        self._debounce = debounce_seconds
        self._recent = {}  # path -> timestamp for debouncing
        self._mutex = QMutex()

    def _should_ignore(self, path):
        """Check if a file event should be ignored."""
        if not path:
            return True

        basename = os.path.basename(path)
        _, ext = os.path.splitext(basename)

        # Ignore by extension
        if ext.lower() in IGNORED_EXTENSIONS:
            return True

        # Ignore hidden files
        if basename.startswith("."):
            return True

        # Ignore specific directories
        parts = path.replace("\\", "/").split("/")
        for part in parts:
            if part in IGNORED_DIRS:
                return True

        return False

    def _is_debounced(self, path):
        """Check if this event is within the debounce window."""
        self._mutex.lock()
        try:
            now = time.time()
            last = self._recent.get(path, 0)
            if now - last < self._debounce:
                return True
            self._recent[path] = now
            # Clean old entries
            cutoff = now - 10
            self._recent = {k: v for k, v in self._recent.items()
                           if v > cutoff}
            return False
        finally:
            self._mutex.unlock()

    def _emit_event(self, event_type, src_path, dest_path=None):
        """Emit a file change event."""
        if self._should_ignore(src_path):
            return
        if self._is_debounced(src_path):
            return

        filename = os.path.basename(src_path)
        directory = os.path.dirname(src_path)

        type_labels = {
            "file_created": "created",
            "file_modified": "modified",
            "file_deleted": "deleted",
            "file_moved": "moved",
        }

        title = f"{filename} {type_labels.get(event_type, 'changed')}"
        description = f"File '{filename}' was {type_labels.get(event_type, 'changed')}"
        description += f"\nDirectory: {directory}"

        metadata = {
            "file_path": src_path,
            "directory": directory,
            "filename": filename,
        }

        # Get file size if file exists
        try:
            if os.path.exists(src_path):
                stat = os.stat(src_path)
                metadata["file_size"] = stat.st_size
                metadata["last_modified"] = datetime.fromtimestamp(
                    stat.st_mtime).isoformat()
        except (OSError, PermissionError):
            pass

        if dest_path:
            metadata["dest_path"] = dest_path
            description += f"\nMoved to: {dest_path}"

        event = {
            "event_type": event_type,
            "category": "FileSystem",
            "source": src_path,
            "title": title,
            "description": description,
            "severity": "info",
            "metadata": metadata,
        }

        self._signal.emit(event)

    def on_created(self, event):
        if not event.is_directory:
            self._emit_event("file_created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._emit_event("file_modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._emit_event("file_deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._emit_event("file_moved", event.src_path, event.dest_path)


class FileMonitor(QThread):
    """Background thread that monitors file system changes."""

    event_detected = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._observer = None
        self._watched_paths = []

    def set_watched_paths(self, paths):
        """Set the list of paths to monitor. Each item: (path, recursive)."""
        self._watched_paths = paths

    def add_watched_path(self, path, recursive=True):
        """Add a path to the watch list."""
        if os.path.isdir(path):
            self._watched_paths.append((path, recursive))
            if self._observer and self._running:
                handler = LogNestEventHandler(self.event_detected)
                self._observer.schedule(handler, path, recursive=recursive)

    def run(self):
        """Main monitoring loop."""
        self._running = True
        logger.info("File monitor started")

        self._observer = Observer()
        handler = LogNestEventHandler(self.event_detected)

        for path, recursive in self._watched_paths:
            if os.path.isdir(path):
                try:
                    self._observer.schedule(handler, path,
                                            recursive=recursive)
                    logger.info(f"Watching: {path} (recursive={recursive})")
                except Exception as e:
                    logger.error(f"Failed to watch {path}: {e}")
                    self.error_occurred.emit(
                        f"Cannot watch '{path}': {e}")

        try:
            self._observer.start()
            while self._running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"File monitor error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=5)

        logger.info("File monitor stopped")

    def stop(self):
        """Stop the file monitor."""
        self._running = False
        if self._observer:
            self._observer.stop()
        self.wait(5000)
