"""
LOG NEST - Process Monitor
Application-level activity tracking similar to Windows Task Manager Apps.
Groups multi-process applications, filters internal subprocesses,
detects closures, tracks durations, and supports configurable application filtering.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Set, Optional, List, Any
from PySide6.QtCore import QThread, Signal

import psutil

from src.database import DatabaseManager
from src.utils.app_metadata import (
    resolve_application_info, get_visible_windows_by_pid,
    get_process_session_id, SYSTEM_AND_HELPER_EXES, AppInfo,
    get_running_taskbar_applications
)
from src.utils.helpers import format_duration

logger = logging.getLogger(__name__)


class ProcessMonitor(QThread):
    """Background thread that monitors user application activity at the application level."""

    event_detected = Signal(dict)   # Emits normalized application event dict
    error_occurred = Signal(str)

    def __init__(self, poll_interval: float = 3.0, parent=None):
        super().__init__(parent)
        self.poll_interval = poll_interval
        self._running = False
        self.db = DatabaseManager()

        # Session tracking state
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # session_key -> session dict
        self._pid_to_session_key: Dict[int, str] = {}         # pid -> session_key
        self._known_pids: Dict[int, Dict[str, Any]] = {}      # pid -> proc info

        # Filtering settings
        self._filter_mode = "all"        # "all", "include", "exclude"
        self._tracked_apps: Set[str] = set()
        self._excluded_apps: Set[str] = set()
        self.reload_filter_settings()

    def reload_filter_settings(self):
        """Reload application filtering configuration from the database."""
        try:
            filters = self.db.get_app_filter_settings()
            self._filter_mode = filters.get("mode", "all")
            self._tracked_apps = {a.lower().strip() for a in filters.get("tracked", []) if a.strip()}
            self._excluded_apps = {a.lower().strip() for a in filters.get("excluded", []) if a.strip()}
            logger.info(f"Process monitor filter loaded: mode={self._filter_mode}, "
                        f"tracked={len(self._tracked_apps)}, excluded={len(self._excluded_apps)}")
        except Exception as e:
            logger.warning(f"Could not load process filter settings: {e}")

    def is_app_allowed(self, app_info: AppInfo) -> bool:
        """Check if an application is allowed by the user's filtering rules."""
        if self._filter_mode == "all":
            return True

        app_name_lower = app_info.display_name.lower()
        app_id_lower = app_info.app_id.lower()
        exe_lower = app_info.exe_name.lower()

        if self._filter_mode == "include":
            return (app_name_lower in self._tracked_apps or
                    app_id_lower in self._tracked_apps or
                    exe_lower in self._tracked_apps)

        if self._filter_mode == "exclude":
            return not (app_name_lower in self._excluded_apps or
                        app_id_lower in self._excluded_apps or
                        exe_lower in self._excluded_apps)

        return True

    def run(self):
        """Main monitoring loop."""
        self._running = True
        logger.info("Application process monitor started")

        # Initial baseline snapshot — register existing applications without emitting events
        try:
            self._take_snapshot(emit_events=False)
        except Exception as e:
            logger.error(f"Error during baseline process snapshot: {e}")

        while self._running:
            try:
                self._take_snapshot(emit_events=True)
            except Exception as e:
                logger.error(f"Application process monitor error: {e}", exc_info=True)
                self.error_occurred.emit(str(e))
            time.sleep(self.poll_interval)

        logger.info("Application process monitor stopped")

    def _should_join_session(self, app_info: AppInfo, cmdline: List[str], exe_path: str, parent_session: Dict[str, Any]) -> bool:
        """Determine if a new process belongs to an existing parent application session."""
        # Same application identity
        if app_info.app_id == parent_session["app_id"]:
            return True

        # Known subprocess or helper binary located within the application installation directory
        if app_info.is_subprocess:
            parent_exe = parent_session.get("exe_path", "")
            if parent_exe:
                parent_dir = parent_exe.lower().rsplit("\\", 1)[0]
                if exe_path.lower().startswith(parent_dir):
                    return True
            if app_info.exe_name.lower() in ("conhost.exe", "openconsole.exe", "crashpad_handler.exe"):
                return True

        return False

    def _take_snapshot(self, emit_events: bool = True):
        """Take a snapshot of running taskbar applications and track session transitions."""
        current_apps = get_running_taskbar_applications()

        # Update process census for memory/subprocess counting
        all_procs: Dict[int, Dict[str, Any]] = {}
        for proc in psutil.process_iter(["pid", "name", "exe", "ppid"]):
            try:
                info = proc.info
                pid = info["pid"]
                name = (info.get("name") or "").strip()
                if not name or pid in (0, 4) or name.lower() in SYSTEM_AND_HELPER_EXES:
                    continue
                all_procs[pid] = info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Associate subprocesses to active apps
        for aid, app_data in current_apps.items():
            exe_norm = (app_data["exe_path"] or "").lower()
            app_pids = app_data["pids"]
            for pid, pinfo in all_procs.items():
                if pid in app_pids:
                    continue
                p_exe = (pinfo.get("exe") or "").lower()
                p_ppid = pinfo.get("ppid")
                if (exe_norm and p_exe == exe_norm) or (p_ppid in app_pids):
                    app_pids.add(pid)

        # ─── Application Launches (Taskbar representation appeared) ──
        for aid, app_data in current_apps.items():
            app_info: AppInfo = app_data["app_info"]
            if not self.is_app_allowed(app_info):
                continue

            if aid not in self._active_sessions:
                # Grouped application opened
                start_dt = datetime.now()
                start_iso = start_dt.isoformat()
                app_name = app_data["display_name"]
                exe_path = app_data["exe_path"]
                opened_time_str = start_dt.strftime("%I:%M %p")

                title = app_name
                description = f"Opened at {opened_time_str}"
                if exe_path:
                    description += f"\nExecutable: {exe_path}"

                event_metadata = {
                    "app_id": app_info.app_id,
                    "app_name": app_name,
                    "main_pid": app_data["main_pid"],
                    "executable": exe_path,
                    "opened_at": start_iso,
                    "peak_process_count": len(app_data["pids"]),
                    "username": app_data.get("username", ""),
                }

                db_event_id = None
                db_session_id = None

                if emit_events:
                    try:
                        db_event_id = self.db.insert_event(
                            event_type="app_session",
                            category="Application",
                            title=title,
                            description=description,
                            source=app_name,
                            metadata=event_metadata,
                            severity="info",
                            timestamp=start_iso,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record app event in DB: {e}")

                    try:
                        db_session_id = self.db.create_app_session(
                            app_id=app_info.app_id,
                            app_name=app_name,
                            executable=exe_path,
                            main_pid=app_data["main_pid"],
                            started_at=start_iso,
                            metadata={
                                "username": app_data.get("username", ""),
                                "windows": [w[1] for w in app_data["windows"]],
                                "aumid": app_data.get("aumid"),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record app session in DB: {e}")

                session = {
                    "key": aid,
                    "app_id": app_info.app_id,
                    "display_name": app_name,
                    "category": app_data["category"],
                    "main_pid": app_data["main_pid"],
                    "exe_path": exe_path,
                    "pids": set(app_data["pids"]),
                    "windows": app_data["windows"],
                    "start_dt": start_dt,
                    "start_iso": start_iso,
                    "peak_process_count": len(app_data["pids"]),
                    "db_session_id": db_session_id,
                    "db_event_id": db_event_id,
                    "username": app_data.get("username", ""),
                }
                self._active_sessions[aid] = session

                if emit_events:
                    self._emit_application_event(
                        event_type="app_session",
                        session=session,
                        pid=app_data["main_pid"],
                        timestamp=start_iso,
                        is_update=False,
                    )
            else:
                # Existing application session update
                sess = self._active_sessions[aid]
                sess["windows"] = app_data["windows"]
                sess["pids"].update(app_data["pids"])
                sess["peak_process_count"] = max(sess["peak_process_count"], len(sess["pids"]))
                if sess.get("db_session_id"):
                    try:
                        self.db.update_app_session_process_count(
                            sess["db_session_id"], sess["peak_process_count"]
                        )
                    except Exception:
                        pass

        # ─── Application Closures (Taskbar representation disappeared) ──
        for aid in list(self._active_sessions.keys()):
            if aid not in current_apps:
                session = self._active_sessions.pop(aid)
                end_dt = datetime.now()
                duration_seconds = max((end_dt - session["start_dt"]).total_seconds(), 0.0)
                formatted_duration = format_duration(duration_seconds)
                end_iso = end_dt.isoformat()

                if session.get("db_session_id"):
                    try:
                        self.db.close_app_session(
                            session_id=session["db_session_id"],
                            ended_at=end_iso,
                            duration_seconds=duration_seconds,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update app session closure in DB: {e}")

                if emit_events:
                    self._emit_application_event(
                        event_type="app_session",
                        session=session,
                        pid=session["main_pid"],
                        timestamp=end_iso,
                        duration_seconds=duration_seconds,
                        duration_formatted=formatted_duration,
                        closed_dt=end_dt,
                        closed_iso=end_iso,
                        is_update=True,
                    )

        self._known_pids = all_procs

    def _emit_application_event(
        self,
        event_type: str,
        session: Dict[str, Any],
        pid: int,
        timestamp: str,
        duration_seconds: Optional[float] = None,
        duration_formatted: Optional[str] = None,
        closed_dt: Optional[datetime] = None,
        closed_iso: Optional[str] = None,
        is_update: bool = False,
    ):
        """Maintain a single persisted entry for the whole application session."""
        app_name = session["display_name"]
        exe_path = session.get("exe_path", "")
        db_event_id = session.get("db_event_id")

        opened_time_str = ""
        if isinstance(session.get("start_dt"), datetime):
            opened_time_str = session["start_dt"].strftime("%I:%M %p")

        if is_update and closed_dt:
            closed_time_str = closed_dt.strftime("%I:%M %p")
            dur_text = duration_formatted or "0s"
            description = (
                f"Opened: {opened_time_str}  |  Closed: {closed_time_str}\n"
                f"Session duration: {dur_text}"
            )
            if exe_path:
                description += f"\nExecutable: {exe_path}"
        else:
            description = f"Opened at {opened_time_str}"
            if exe_path:
                description += f"\nExecutable: {exe_path}"

        title = app_name

        metadata = {
            "app_id": session["app_id"],
            "app_name": app_name,
            "main_pid": pid,
            "executable": exe_path,
            "session_db_id": session.get("db_session_id"),
            "peak_process_count": session.get("peak_process_count", 1),
            "username": session.get("username", ""),
            "opened_at": session.get("start_iso", timestamp),
            "state": "closed" if closed_dt else "opened",
        }
        if closed_iso:
            metadata["closed_at"] = closed_iso
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
            metadata["duration_formatted"] = duration_formatted

        if closed_dt:
            if db_event_id:
                self.db.update_event(db_event_id, title=title,
                                     description=description, metadata=metadata)
            else:
                # Apps present at the initial baseline have no open event yet.
                db_event_id = self.db.insert_event(
                    event_type=event_type, category="Application", title=title,
                    description=description, source=app_name, metadata=metadata,
                    severity="info", timestamp=session["start_iso"],
                )
                is_update = False

        event = {
            "id": db_event_id,
            "is_update": bool(closed_dt and is_update),
            "event_type": event_type,
            "category": "Application",
            "source": app_name,
            "title": title,
            "description": description,
            "severity": "info",
            "timestamp": session.get("start_iso", timestamp),
            "metadata": metadata,
        }

        self.event_detected.emit(event)

    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        self.wait(5000)

    def get_active_process_count(self) -> int:
        """Get count of tracked processes across all active applications."""
        return len(self._known_pids)

    def get_active_app_count(self) -> int:
        """Get count of currently active application sessions."""
        return len(self._active_sessions)

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active application sessions."""
        return list(self._active_sessions.values())
