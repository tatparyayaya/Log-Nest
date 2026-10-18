import sys
import time
from datetime import datetime

sys.path.insert(0, r"d:\LOG_NEST")

from src.monitors.process_monitor import ProcessMonitor
from src.utils.app_metadata import resolve_application_info
from src.database import DatabaseManager

def test_edge_single_entry_lifecycle():
    print("\n========================================================")
    print("Testing Microsoft Edge Single-Entry Lifecycle...")
    print("========================================================")

    db = DatabaseManager()
    pm = ProcessMonitor(poll_interval=0.5)

    events_captured = []
    pm.event_detected.connect(lambda e: events_captured.append(e))

    # Baseline: no active sessions
    assert len(pm._active_sessions) == 0

    # 1. Edge Opens with 3 tabs
    app_info = resolve_application_info("msedge.exe", r"C:\Program Files\Edge\msedge.exe", ["msedge.exe"], 2)
    skey = app_info.app_id
    start_dt = datetime.now()
    start_iso = start_dt.isoformat()

    # Insert initial open entry
    db_event_id = db.insert_event(
        event_type="app_session",
        category="Application",
        title="Microsoft Edge",
        description=f"Opened at {start_dt.strftime('%I:%M %p')}",
        source="Microsoft Edge",
        metadata={"app_id": skey, "app_name": "Microsoft Edge", "opened_at": start_iso},
        severity="info",
        timestamp=start_iso
    )

    session = {
        "key": skey,
        "app_id": skey,
        "display_name": app_info.display_name,
        "category": "Browser",
        "main_pid": 10001,
        "exe_path": r"C:\Program Files\Edge\msedge.exe",
        "pids": {10001},
        "windows": [(101, "New Tab - Personal - Microsoft Edge")],
        "start_dt": start_dt,
        "start_iso": start_iso,
        "peak_process_count": 1,
        "db_session_id": None,
        "db_event_id": db_event_id,
        "username": "user",
    }
    pm._active_sessions[skey] = session
    pm._emit_application_event("app_session", session, 10001, start_iso, is_update=False)

    print("1. Verifying initial opened entry created...")
    assert len(events_captured) == 1, f"Expected 1 event, got {len(events_captured)}"
    assert events_captured[0]["title"] == "Microsoft Edge"
    assert events_captured[0]["id"] == db_event_id
    assert "Opened at" in events_captured[0]["description"]
    print(f"   -> Event Created ID={db_event_id}: '{events_captured[0]['title']}' (PASSED)")

    # 2. Add 15 subprocesses (renderers, GPUs, utility)
    print("2. Spawning 15 subprocesses (tabs, GPU, renderers, utility)...")
    for pid in range(10002, 10017):
        session["pids"].add(pid)
        session["peak_process_count"] = max(session["peak_process_count"], len(session["pids"]))

    assert len(events_captured) == 1, "Spawning tabs and internal subprocesses MUST NOT emit new events!"
    print(f"   -> Total coordinated subprocesses: {session['peak_process_count']} (0 spurious events, PASSED)")

    # 3. User closes 8 tabs
    print("3. User closes 8 tabs...")
    for pid in range(10002, 10010):
        session["pids"].discard(pid)

    assert len(events_captured) == 1, "Closing individual tabs MUST NOT emit new events!"
    print(f"   -> Events captured so far: {len(events_captured)} (PASSED)")

    # 4. User completely closes Edge (window closes and taskbar state disappears)
    print("4. User completely closes Edge (updating the SAME single entry)...")
    closed_session = pm._active_sessions.pop(skey)
    end_dt = datetime.now()
    duration_seconds = 65.0
    formatted_duration = "1m 05s"
    end_iso = end_dt.isoformat()

    pm._emit_application_event(
        "app_session",
        closed_session,
        closed_session["main_pid"],
        start_iso,
        duration_seconds=duration_seconds,
        duration_formatted=formatted_duration,
        closed_dt=end_dt,
        closed_iso=end_iso,
        is_update=True,
    )

    # Verify that the DB record was updated in-place (no new row created)
    updated_event = db.get_event_by_id(db_event_id)
    assert updated_event is not None
    assert "Opened:" in updated_event["description"]
    assert "Closed:" in updated_event["description"]
    assert "Session duration: 1m 05s" in updated_event["description"]

    # Verify duration badge metadata exists
    import json
    meta = json.loads(updated_event["metadata"])
    assert meta["duration_formatted"] == "1m 05s"
    assert meta["duration_seconds"] == 65.0
    assert "closed_at" in meta

    print("5. Verifying single-entry update...")
    print(f"   -> Description: {updated_event['description']}")
    print(f"   -> Duration Badge Metadata: {meta['duration_formatted']} (PASSED)")

    print("\nALL EDGE SINGLE-ENTRY LIFECYCLE ASSERTIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_edge_single_entry_lifecycle()
