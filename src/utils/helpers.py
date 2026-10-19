"""
LOG NEST - Utility helpers
Common helper functions used across the application.
"""

import os
import json
from datetime import datetime, timedelta


def format_timestamp(iso_string, fmt="%I:%M %p"):
    """Format an ISO timestamp into a human-readable string."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return iso_string or ""


def format_timestamp_full(iso_string):
    """Format an ISO timestamp with date and time."""
    return format_timestamp(iso_string, "%b %d, %Y  %I:%M:%S %p")


def relative_time(iso_string):
    """Return a relative time string like '5 minutes ago'."""
    try:
        dt = datetime.fromisoformat(iso_string)
        now = datetime.now()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            mins = int(diff.total_seconds() / 60)
            return f"{mins}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return dt.strftime("%b %d")
    except (ValueError, TypeError):
        return ""


def format_bytes(size_bytes):
    """Format bytes into human-readable size."""
    if size_bytes is None:
        return "N/A"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_path(path, max_len=60):
    """Truncate a file path for display, keeping the filename visible."""
    if not path or len(path) <= max_len:
        return path or ""
    parts = path.replace("\\", "/").split("/")
    filename = parts[-1]
    if len(filename) >= max_len - 5:
        return "..." + filename[-(max_len - 3):]
    # Keep drive + ... + last N components
    result = parts[0] + "/..."
    i = len(parts) - 1
    while i > 0 and len(result) + len(parts[i]) + 1 < max_len:
        result = result[:len(parts[0]) + 4] + "/" + "/".join(parts[i:])
        i -= 1
        if len(result) > max_len:
            break
    return result if len(result) <= max_len else parts[0] + "/.../" + filename


def safe_json_loads(text, default=None):
    """Safely parse JSON, returning default on failure."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def get_app_data_dir():
    """Get the application data directory."""
    path = os.path.join(os.path.expanduser("~"), ".lognest")
    os.makedirs(path, exist_ok=True)
    return path


def format_duration(seconds):
    """Format duration in seconds into a friendly human-readable string."""
    if seconds is None or seconds < 0:
        return "0s"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    mins, secs = divmod(seconds, 60)
    if mins < 60:
        return f"{mins}m {secs:02d}s"
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins:02d}m"


def format_screen_time(seconds, detailed=False):
    """Format screen time in Android Digital Wellbeing style (e.g. '2 hr 15 min', '45 min', '12 sec')."""
    if seconds is None or seconds <= 0:
        return "0 min" if not detailed else "0 sec"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} sec" if detailed else "< 1 min"
    mins, secs = divmod(seconds, 60)
    if mins < 60:
        if detailed and secs > 0:
            return f"{mins} min {secs} sec"
        return f"{mins} min"
    hours, mins = divmod(mins, 60)
    if mins == 0:
        return f"{hours} hr"
    return f"{hours} hr {mins} min"


# Category icons (Unicode)
CATEGORY_ICONS = {
    "Application": "🔷",
    "FileSystem": "📁",
    "System": "⚙️",
    "Crash": "💥",
}

# Severity colors (hex)
SEVERITY_COLORS = {
    "info": "#4FC3F7",
    "warning": "#FFB74D",
    "error": "#EF5350",
    "critical": "#FF1744",
}

# Event type display names
EVENT_TYPE_LABELS = {
    "app_session": "Application Session",
    "app_opened": "Application Opened",
    "app_closed": "Application Closed",
    "process_start": "Process Started",
    "process_exit": "Process Exited",
    "file_created": "File Created",
    "file_modified": "File Modified",
    "file_deleted": "File Deleted",
    "file_moved": "File Moved",
    "system_event": "System Event",
    "system_error": "System Error",
    "system_warning": "System Warning",
    "crash": "Application Crash",
}


def get_event_icon(event_type):
    """Get an icon character for an event type."""
    icons = {
        "app_session": "🖥️",
        "app_opened": "▶",
        "app_closed": "⏹",
        "process_start": "▶",
        "process_exit": "⏹",
        "file_created": "✚",
        "file_modified": "✎",
        "file_deleted": "✖",
        "file_moved": "↔",
        "system_event": "ℹ",
        "system_error": "⚠",
        "system_warning": "⚠",
        "crash": "💥",
    }
    return icons.get(event_type, "●")

