"""
LOG NEST - Database Manager
SQLite database with FTS5 full-text search for event storage and retrieval.
"""

import sqlite3
import json
import os
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager


class DatabaseManager:
    """Thread-safe SQLite database manager for LOG NEST events."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path=None):
        if self._initialized:
            return
        if db_path is None:
            app_data = os.path.join(os.path.expanduser("~"), ".lognest")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "lognest.db")
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._initialized = True

    def _get_conn(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                timeout=10,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        return self._local.conn

    @contextmanager
    def _cursor(self):
        """Context manager for database operations with automatic commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self):
        """Initialize database tables and indexes."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Main events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT,
                title TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                severity TEXT DEFAULT 'info',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_category
            ON events(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_severity
            ON events(severity)
        """)

        # Full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                title, description, source,
                content=events,
                content_rowid=id,
                tokenize='porter unicode61'
            )
        """)

        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
                INSERT INTO events_fts(rowid, title, description, source)
                VALUES (new.id, new.title, new.description, new.source);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, source)
                VALUES ('delete', old.id, old.title, old.description, old.source);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, source)
                VALUES ('delete', old.id, old.title, old.description, old.source);
                INSERT INTO events_fts(rowid, title, description, source)
                VALUES (new.id, new.title, new.description, new.source);
            END
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Monitored paths table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                recursive INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1
            )
        """)

        # Application sessions table for logical session tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                executable TEXT,
                main_pid INTEGER,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds REAL,
                status TEXT DEFAULT 'active',
                open_event_id INTEGER,
                close_event_id INTEGER,
                process_count INTEGER DEFAULT 1,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_sessions_status
            ON app_sessions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_sessions_started
            ON app_sessions(started_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_sessions_app_id
            ON app_sessions(app_id)
        """)

        conn.commit()

        # Run safe migration on first launch with new version
        self._check_and_run_migration(cursor, conn)


    def insert_event(self, event_type, category, title, description="",
                     source="", metadata=None, severity="info", timestamp=None):
        """Insert a new event into the database."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, category, source,
                                    title, description, metadata, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, event_type, category, source,
                  title, description, metadata_json, severity))
            return cursor.lastrowid

    def update_event(self, event_id, title=None, description=None, metadata=None, severity=None, event_type=None):
        """Update an existing event record in the database."""
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata) if isinstance(metadata, (dict, list)) else metadata)
        if severity is not None:
            updates.append("severity = ?")
            params.append(severity)
        if event_type is not None:
            updates.append("event_type = ?")
            params.append(event_type)

        if not updates:
            return

        params.append(event_id)
        with self._cursor() as cursor:
            cursor.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", params)

    def get_event_by_id(self, event_id):
        """Get a single event by its ID."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_events(self, limit=100, offset=0, category=None, event_type=None,
                   severity=None, start_date=None, end_date=None,
                   order="DESC"):
        """Get events with optional filtering."""
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if severity:
            if isinstance(severity, list):
                placeholders = ",".join("?" * len(severity))
                query += f" AND severity IN ({placeholders})"
                params.extend(severity)
            else:
                query += " AND severity = ?"
                params.append(severity)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += f" ORDER BY timestamp {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_events(self, query_text, limit=50, category=None,
                      start_date=None, end_date=None):
        """Full-text search across events using FTS5."""
        # Sanitize query for FTS5
        safe_query = query_text.replace('"', '""')
        fts_query = f'"{safe_query}"'

        sql = """
            SELECT e.*, rank
            FROM events e
            JOIN events_fts ON e.id = events_fts.rowid
            WHERE events_fts MATCH ?
        """
        params = [fts_query]

        if category:
            sql += " AND e.category = ?"
            params.append(category)
        if start_date:
            sql += " AND e.timestamp >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND e.timestamp <= ?"
            params.append(end_date)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self._cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_events_around(self, event_id, window_minutes=5, limit=20):
        """Get events that occurred before and after a specific event."""
        with self._cursor() as cursor:
            # Get the target event's timestamp
            cursor.execute("SELECT timestamp FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            if not row:
                return {"before": [], "after": [], "target": None}

            target_ts = row["timestamp"]
            target_dt = datetime.fromisoformat(target_ts)
            before_ts = (target_dt - timedelta(minutes=window_minutes)).isoformat()
            after_ts = (target_dt + timedelta(minutes=window_minutes)).isoformat()

            # Get target event
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            target = dict(cursor.fetchone())

            # Get events before
            cursor.execute("""
                SELECT * FROM events
                WHERE timestamp >= ? AND timestamp < ? AND id != ?
                ORDER BY timestamp DESC LIMIT ?
            """, (before_ts, target_ts, event_id, limit))
            before = [dict(r) for r in cursor.fetchall()]

            # Get events after
            cursor.execute("""
                SELECT * FROM events
                WHERE timestamp > ? AND timestamp <= ? AND id != ?
                ORDER BY timestamp ASC LIMIT ?
            """, (target_ts, after_ts, event_id, limit))
            after = [dict(r) for r in cursor.fetchall()]

            return {"before": before, "target": target, "after": after}

    def get_stats(self, hours=24):
        """Get event statistics for the dashboard."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            stats = {}

            # Total events
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM events WHERE timestamp >= ?",
                (since,))
            stats["total_events"] = cursor.fetchone()["cnt"]

            # By category
            cursor.execute("""
                SELECT category, COUNT(*) as cnt FROM events
                WHERE timestamp >= ?
                GROUP BY category ORDER BY cnt DESC
            """, (since,))
            stats["by_category"] = {r["category"]: r["cnt"]
                                     for r in cursor.fetchall()}

            # By severity
            cursor.execute("""
                SELECT severity, COUNT(*) as cnt FROM events
                WHERE timestamp >= ?
                GROUP BY severity ORDER BY cnt DESC
            """, (since,))
            stats["by_severity"] = {r["severity"]: r["cnt"]
                                     for r in cursor.fetchall()}

            # By hour (for chart)
            cursor.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as cnt
                FROM events WHERE timestamp >= ?
                GROUP BY hour ORDER BY hour
            """, (since,))
            stats["by_hour"] = {r["hour"]: r["cnt"]
                                for r in cursor.fetchall()}

            # Top sources
            cursor.execute("""
                SELECT source, COUNT(*) as cnt FROM events
                WHERE timestamp >= ? AND source != ''
                GROUP BY source ORDER BY cnt DESC LIMIT 10
            """, (since,))
            stats["top_sources"] = {r["source"]: r["cnt"]
                                     for r in cursor.fetchall()}

            # Error/crash count
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM events
                WHERE timestamp >= ? AND severity IN ('error', 'critical')
            """, (since,))
            stats["error_count"] = cursor.fetchone()["cnt"]

            return stats

    def get_hourly_activity(self, hours=24):
        """Get hourly event counts for chart display."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT
                    strftime('%Y-%m-%dT%H:00:00', timestamp) as hour_bucket,
                    category,
                    COUNT(*) as cnt
                FROM events
                WHERE timestamp >= ?
                GROUP BY hour_bucket, category
                ORDER BY hour_bucket
            """, (since,))
            return [dict(r) for r in cursor.fetchall()]

    # --- Settings ---
    def get_setting(self, key, default=None):
        """Get a setting value."""
        with self._cursor() as cursor:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        """Set a setting value."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """, (key, str(value)))

    # --- Monitored Paths ---
    def get_monitored_paths(self):
        """Get all monitored paths."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM monitored_paths WHERE active = 1")
            return [dict(r) for r in cursor.fetchall()]

    def add_monitored_path(self, path, recursive=True):
        """Add a path to monitor."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR IGNORE INTO monitored_paths (path, recursive, active)
                VALUES (?, ?, 1)
            """, (path, int(recursive)))
            return cursor.lastrowid

    def remove_monitored_path(self, path_id):
        """Remove a monitored path (soft delete)."""
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE monitored_paths SET active = 0 WHERE id = ?",
                (path_id,))

    # --- Maintenance ---
    def cleanup_old_events(self, days=30):
        """Delete events older than the specified number of days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM events WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            cursor.execute("DELETE FROM events_fts WHERE rowid NOT IN (SELECT id FROM events)")
            return deleted

    def get_event_count(self):
        """Get total event count."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM events")
            return cursor.fetchone()["cnt"]

    # --- Application Sessions ---
    def create_app_session(self, app_id, app_name, executable, main_pid,
                           started_at=None, open_event_id=None, metadata=None):
        """Create a new logical application session record."""
        if started_at is None:
            started_at = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO app_sessions (app_id, app_name, executable, main_pid,
                                         started_at, status, open_event_id,
                                         process_count, metadata)
                VALUES (?, ?, ?, ?, ?, 'active', ?, 1, ?)
            """, (app_id, app_name, executable, main_pid, started_at,
                  open_event_id, metadata_json))
            return cursor.lastrowid

    def close_app_session(self, session_id, ended_at=None, duration_seconds=None,
                          close_event_id=None):
        """Mark an application session as closed and store duration."""
        if ended_at is None:
            ended_at = datetime.now().isoformat()
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE app_sessions
                SET status = 'closed',
                    ended_at = ?,
                    duration_seconds = ?,
                    close_event_id = ?
                WHERE id = ?
            """, (ended_at, duration_seconds, close_event_id, session_id))

    def update_app_session_process_count(self, session_id, count):
        """Update peak process count for an application session."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE app_sessions
                SET process_count = MAX(process_count, ?)
                WHERE id = ?
            """, (count, session_id))

    def get_active_app_sessions(self):
        """Get all currently active application sessions."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM app_sessions WHERE status = 'active' ORDER BY started_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_app_session(self, session_id):
        """Get an application session by ID."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM app_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Application Filter Settings ---
    def get_app_filter_settings(self):
        """Get configured application filtering settings."""
        mode = self.get_setting("app_filter_mode", "all")
        tracked_json = self.get_setting("app_filter_tracked", "[]")
        excluded_json = self.get_setting("app_filter_excluded", "[]")
        try:
            tracked = json.loads(tracked_json)
        except Exception:
            tracked = []
        try:
            excluded = json.loads(excluded_json)
        except Exception:
            excluded = []
        return {
            "mode": mode,
            "tracked": tracked,
            "excluded": excluded,
        }

    def set_app_filter_settings(self, mode="all", tracked=None, excluded=None):
        """Save application filter settings."""
        self.set_setting("app_filter_mode", mode)
        if tracked is not None:
            self.set_setting("app_filter_tracked", json.dumps(tracked))
        if excluded is not None:
            self.set_setting("app_filter_excluded", json.dumps(excluded))

    # --- Migration ---
    def _check_and_run_migration(self, cursor, conn):
        """Check if legacy process events need safe normalization."""
        cursor.execute("SELECT value FROM settings WHERE key = 'process_migration_v1'")
        row = cursor.fetchone()
        if not row or row["value"] != "done":
            self._migrate_legacy_events(cursor)
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('process_migration_v1', 'done')
            """)
            conn.commit()

    def _migrate_legacy_events(self, cursor):
        """Safely migrate legacy process events to clean application names."""
        try:
            from src.utils.app_metadata import resolve_application_info
            cursor.execute("""
                SELECT id, title, source, event_type, metadata
                FROM events
                WHERE category = 'Application'
                  AND event_type IN ('process_start', 'process_exit')
            """)
            rows = cursor.fetchall()
            for r in rows:
                event_id = r["id"]
                title = r["title"] or ""
                source = r["source"] or ""
                event_type = r["event_type"]

                exe_name = source
                if not exe_name and (" started" in title or " exited" in title):
                    exe_name = title.replace(" started", "").replace(" exited", "").strip()

                if exe_name:
                    app_info = resolve_application_info(exe_name)
                    clean_name = app_info.display_name

                    new_type = "app_opened" if event_type == "process_start" else "app_closed"
                    action_word = "Opened" if event_type == "process_start" else "Closed"
                    new_title = f"{clean_name} — {action_word}"

                    cursor.execute("""
                        UPDATE events
                        SET title = ?, source = ?, event_type = ?
                        WHERE id = ?
                    """, (new_title, clean_name, new_type, event_id))
        except Exception:
            pass

    def export_events(self, filepath, start_date=None, end_date=None):
        """Export events to a JSON file."""
        events = self.get_events(
            limit=999999, start_date=start_date, end_date=end_date)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        return len(events)

    def close(self):
        """Close the thread-local connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

