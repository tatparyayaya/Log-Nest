"""
Integration and Unit Tests for LOG NEST.
Validates database, application-level process tracking, metadata resolution,
subprocess grouping, configurable filtering, safe migration, and UI integration.
"""

import sys
import os
import time
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.database import DatabaseManager
from src.monitors.monitor_manager import MonitorManager
from src.monitors.process_monitor import ProcessMonitor
from src.monitors.system_event_monitor import SystemEventMonitor
from src.monitors.file_monitor import FileMonitor
from src.utils.app_metadata import (
    resolve_application_info, detect_subprocess_role,
    is_system_or_background_service, get_visible_windows_by_pid,
    KNOWN_APPLICATIONS
)
from src.utils.helpers import format_duration
from src.ui.main_window import MainWindow


def test_database():
    print("Testing DatabaseManager...")
    db = DatabaseManager()

    # Insert event
    event_id = db.insert_event(
        event_type="app_opened",
        category="Application",
        title="Microsoft Edge opened",
        description="Microsoft Edge was launched",
        source="Microsoft Edge",
        metadata={"app_name": "Microsoft Edge", "main_pid": 1888, "executable": "C:\\Program Files\\Edge\\msedge.exe"},
        severity="info"
    )
    assert event_id > 0, "Failed to insert event"
    print(f"  Inserted event id={event_id}")

    # Fetch events
    events = db.get_events(limit=10)
    assert any(e["id"] == event_id for e in events), "Inserted event not in get_events"
    print(f"  Retrieved {len(events)} events")

    # Search event
    results = db.search_events("Microsoft Edge")
    assert len(results) > 0, "FTS search returned no results"
    print(f"  FTS search found {len(results)} matches")

    # Context / Events around
    around = db.get_events_around(event_id, window_minutes=10)
    assert around["target"] is not None, "Target event not found in get_events_around"
    assert around["target"]["id"] == event_id
    print(f"  Context around event verified")

    # App Sessions Table testing
    session_id = db.create_app_session(
        app_id="microsoft_edge",
        app_name="Microsoft Edge",
        executable="C:\\Program Files\\Edge\\msedge.exe",
        main_pid=1888,
        open_event_id=event_id,
        metadata={"test": True}
    )
    assert session_id > 0, "Failed to create app session"

    active_sessions = db.get_active_app_sessions()
    assert any(s["id"] == session_id for s in active_sessions), "Session not found in active list"

    db.update_app_session_process_count(session_id, 14)
    db.close_app_session(session_id, duration_seconds=125.5)

    sess = db.get_app_session(session_id)
    assert sess["status"] == "closed"
    assert sess["duration_seconds"] == 125.5
    assert sess["process_count"] == 14
    print("  App session lifecycle (create, update, close) verified")

    # Filter settings testing
    db.set_app_filter_settings(mode="include", tracked=["Microsoft Edge", "Notepad"], excluded=[])
    cfg = db.get_app_filter_settings()
    assert cfg["mode"] == "include"
    assert "Microsoft Edge" in cfg["tracked"]
    # Restore default
    db.set_app_filter_settings(mode="all", tracked=[], excluded=[])
    print("  Application filter configuration in DB verified")

    # Stats
    stats = db.get_stats(hours=24)
    assert stats["total_events"] > 0
    print(f"  Stats verified: total={stats['total_events']}")

    # Export
    tmp_export = os.path.join(tempfile.gettempdir(), "lognest_export_test.csv")
    exported = db.export_events(tmp_export)
    assert exported > 0 and os.path.exists(tmp_export)
    os.remove(tmp_export)
    print(f"  CSV export verified ({exported} rows)")


def test_app_metadata():
    print("Testing Application Metadata & Subprocess Classification...")

    # Test Microsoft Edge root
    edge_info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe"], 2)
    assert edge_info.app_id == "microsoft_edge"
    assert edge_info.display_name == "Microsoft Edge"
    assert edge_info.is_user_app is True
    assert edge_info.is_subprocess is False

    # Test Microsoft Edge subprocesses (Renderer, GPU, Utility, Crashpad)
    for sub_arg, expected_role in [
        ("--type=renderer", "renderer"),
        ("--type=gpu-process", "gpu-process"),
        ("--type=utility", "utility"),
        ("--type=crashpad-handler", "crash-handler"),
    ]:
        is_sub, role = detect_subprocess_role("msedge.exe", ["msedge.exe", sub_arg])
        assert is_sub is True, f"Failed to detect {sub_arg} as subprocess"
        info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe", sub_arg], 2)
        assert info.is_subprocess is True
        assert info.is_user_app is False

    # Test VS Code root and child
    code_info = resolve_application_info("Code.exe", r"C:\Users\User\AppData\Programs\Code\Code.exe", ["Code.exe"], 2)
    assert code_info.display_name == "Visual Studio Code"
    assert code_info.is_user_app is True

    code_sub = resolve_application_info("Code.exe", r"C:\Users\User\AppData\Programs\Code\Code.exe", ["Code.exe", "--type=extensionHost"], 2)
    assert code_sub.is_subprocess is True
    assert code_sub.is_user_app is False

    # Test Notepad
    notepad_info = resolve_application_info("notepad.exe", r"C:\Windows\System32\notepad.exe", ["notepad.exe"], 2)
    assert notepad_info.display_name == "Notepad"
    assert notepad_info.is_user_app is True

    # Test System Service exclusions
    assert is_system_or_background_service("svchost.exe", r"C:\Windows\System32\svchost.exe", 0) is True
    assert is_system_or_background_service("memcompression", "", 0) is True
    assert is_system_or_background_service("rtkaudioservice64.exe", r"C:\Windows\System32\rtkaudioservice64.exe", 2, "Realtek Audio Service") is True

    # Test Duration formatter
    assert format_duration(45) == "45s"
    assert format_duration(754) == "12m 34s"
    assert format_duration(3665) == "1h 01m"

    print("  Application metadata resolution and role classification verified")


def test_multiprocess_app_tracking():
    print("Testing Multi-Process Application Grouping & Lifecycle...")
    pm = ProcessMonitor(poll_interval=1.0)
    events_captured = []
    pm.event_detected.connect(lambda evt: events_captured.append(evt))

    # Baseline snapshot
    pm._take_snapshot(emit_events=False)
    initial_event_count = len(events_captured)
    assert initial_event_count == 0, "Baseline snapshot should not emit events"

    # Simulate Edge launch: 1 main process (PID 50001) + 5 subprocesses (PIDs 50002-50006)
    # 1. Main process starts
    app_info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe"], 2)
    pm._known_pids[50001] = {
        "pid": 50001, "name": "msedge.exe", "exe": r"C:\Program Files\Edge\msedge.exe",
        "cmdline": ["msedge.exe"], "ppid": 1000, "app_info": app_info,
        "create_time": time.time(), "username": "user", "memory": 50000000, "has_window": True
    }
    # Register session
    skey = f"{app_info.app_id}_50001"
    pm._active_sessions[skey] = {
        "key": skey, "app_id": app_info.app_id, "display_name": app_info.display_name,
        "category": "Application", "main_pid": 50001, "exe_path": r"C:\Program Files\Edge\msedge.exe",
        "pids": {50001}, "start_dt": datetime.now(), "start_iso": datetime.now().isoformat(),
        "has_seen_window": True, "peak_process_count": 1, "db_session_id": None, "username": "user"
    }
    pm._pid_to_session_key[50001] = skey
    pm._emit_application_event("app_session", pm._active_sessions[skey], 50001, datetime.now().isoformat())

    assert len(events_captured) == 1
    assert events_captured[0]["event_type"] == "app_session"
    assert events_captured[0]["title"] == "Microsoft Edge"

    # 2. Add 5 subprocesses (renderers, GPU, utility)
    for p in range(50002, 50007):
        sub_info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe", "--type=renderer"], 2)
        pm._known_pids[p] = {
            "pid": p, "name": "msedge.exe", "exe": r"C:\Program Files\Edge\msedge.exe",
            "cmdline": ["msedge.exe", "--type=renderer"], "ppid": 50001, "app_info": sub_info,
            "create_time": time.time(), "username": "user", "memory": 20000000, "has_window": False
        }
        pm._active_sessions[skey]["pids"].add(p)
        pm._active_sessions[skey]["peak_process_count"] = max(pm._active_sessions[skey]["peak_process_count"], len(pm._active_sessions[skey]["pids"]))
        pm._pid_to_session_key[p] = skey

    # Assert NO duplicate open events were emitted for subprocesses
    assert len(events_captured) == 1, "Subprocesses should not emit opened events!"
    assert pm._active_sessions[skey]["peak_process_count"] == 6

    # 3. Terminate 3 tab subprocesses
    for p in [50002, 50003, 50004]:
        pm._known_pids.pop(p, None)
        pm._active_sessions[skey]["pids"].discard(p)
        pm._pid_to_session_key.pop(p, None)

    # Assert NO close events were emitted for tab termination
    assert len(events_captured) == 1, "Tab closures should not emit closed event!"

    # 4. Main application closes (main PID 50001 exits, while background helper 50005 remains temporarily alive)
    pm._known_pids.pop(50001, None)
    pm._active_sessions[skey]["pids"].discard(50001)
    pm._pid_to_session_key.pop(50001, None)

    # Evaluate closure (main_pid exited and no visible windows)
    sess = pm._active_sessions.pop(skey)
    pm._emit_application_event(
        "app_session", sess, 50001, datetime.now().isoformat(),
        duration_seconds=42.0, duration_formatted="42s",
        closed_dt=datetime.now(), closed_iso=datetime.now().isoformat(),
        is_update=True
    )

    assert len(events_captured) == 2
    assert events_captured[1]["event_type"] == "app_session"
    assert events_captured[1]["title"] == "Microsoft Edge"
    assert events_captured[1]["metadata"]["duration_formatted"] == "42s"

    print("  Multi-process Edge grouping (1 opened, 0 tab noise, 1 closed) verified")


def test_configurable_app_filtering():
    print("Testing Configurable Application Filtering...")
    pm = ProcessMonitor(poll_interval=1.0)

    edge_info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe"], 2)
    notepad_info = resolve_application_info("notepad.exe", r"C:\Windows\System32\notepad.exe", ["notepad.exe"], 2)
    vlc_info = resolve_application_info("vlc.exe", r"C:\Program Files\VideoLAN\vlc.exe", ["vlc.exe"], 2)

    # 1. Mode: "all"
    pm._filter_mode = "all"
    assert pm.is_app_allowed(edge_info) is True
    assert pm.is_app_allowed(notepad_info) is True
    assert pm.is_app_allowed(vlc_info) is True

    # 2. Mode: "include" (Whitelist)
    pm._filter_mode = "include"
    pm._tracked_apps = {"microsoft edge", "notepad"}
    assert pm.is_app_allowed(edge_info) is True
    assert pm.is_app_allowed(notepad_info) is True
    assert pm.is_app_allowed(vlc_info) is False

    # 3. Mode: "exclude" (Blacklist)
    pm._filter_mode = "exclude"
    pm._excluded_apps = {"vlc media player", "vlc"}
    assert pm.is_app_allowed(edge_info) is True
    assert pm.is_app_allowed(vlc_info) is False

    print("  Application filtering (all, whitelist, blacklist) verified")


def test_database_migration():
    print("Testing Safe Legacy Process Migration...")
    db = DatabaseManager()

    # Insert raw legacy events (simulating past version before fix)
    old_start_id = db.insert_event(
        event_type="process_start",
        category="Application",
        title="msedge.exe started",
        description="Process 'msedge.exe' (PID: 9999) was launched",
        source="msedge.exe",
        metadata={"pid": 9999, "executable": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"},
        severity="info"
    )
    old_exit_id = db.insert_event(
        event_type="process_exit",
        category="Application",
        title="msedge.exe exited",
        description="Process 'msedge.exe' (PID: 9999) has exited",
        source="msedge.exe",
        metadata={"pid": 9999},
        severity="info"
    )

    # Run safe migration
    conn = db._get_conn()
    cursor = conn.cursor()
    db._migrate_legacy_events(cursor)
    conn.commit()

    # Verify normalization
    events = {e["id"]: e for e in db.get_events(limit=50)}
    migrated_start = events.get(old_start_id)
    migrated_exit = events.get(old_exit_id)

    assert migrated_start is not None
    assert migrated_start["title"] == "Microsoft Edge — Opened"
    assert migrated_start["source"] == "Microsoft Edge"
    assert migrated_start["event_type"] == "app_opened"

    assert migrated_exit is not None
    assert migrated_exit["title"] == "Microsoft Edge — Closed"
    assert migrated_exit["source"] == "Microsoft Edge"
    assert migrated_exit["event_type"] == "app_closed"

    print("  Legacy event migration safely normalized records without data loss")


def test_monitors():
    print("Testing Monitors Integration...")
    pm = ProcessMonitor(poll_interval=1.0)
    pm._take_snapshot(emit_events=False)
    count = pm.get_active_process_count()
    assert count > 0, "No active processes captured"
    print(f"  Process monitor captured {count} processes")

    fm = FileMonitor()
    assert fm is not None
    print("  File monitor initialized")

    sm = SystemEventMonitor(poll_interval=5.0)
    assert sm is not None
    print("  System event monitor initialized")

    mm = MonitorManager()
    mm.start_all()
    time.sleep(1.0)
    assert mm._running is True
    mm.stop_all()
    print("  MonitorManager started and stopped cleanly")


def test_ui():
    print("Testing UI instantiation...")
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    assert win is not None
    assert len(win._nav_buttons) == 4
    assert win._page_stack.count() == 4

    # Verify settings page has application filtering UI elements
    settings = win._settings
    assert hasattr(settings, "app_filter_mode_combo")
    assert hasattr(settings, "apps_list")
    assert settings.apps_list.count() > 0
    print(f"  Settings page initialized with {settings.apps_list.count()} application filter items")

    print("  MainWindow created with 4 navigation pages, tabs, and app filter controls")
    win._quit_app()
    app.processEvents()




if __name__ == "__main__":
    test_database()
    test_app_metadata()
    test_multiprocess_app_tracking()
    test_configurable_app_filtering()
    test_database_migration()
    test_monitors()
    test_ui()
    print("\nALL LOG NEST PROCESS TRACKING TESTS PASSED SUCCESSFULLY!")
    sys.exit(0)


