"""
LOG NEST - Settings Page
Application settings, monitored paths management, and data controls.
"""

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QCheckBox, QSpinBox,
    QFileDialog, QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QGridLayout, QLineEdit, QComboBox
)

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap

from src.database import DatabaseManager
from src.ui.theme import COLORS


class SettingsPage(QWidget):
    """Settings page for configuring monitors, paths, and data management."""

    monitors_changed = Signal()  # Emitted when monitor settings change
    paths_changed = Signal()     # Emitted when monitored paths change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Build the settings UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header
        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; "
            f"color: {COLORS['text_primary']};"
        )
        main_layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        # ─── Monitor Settings ────────────────────────────────────
        monitor_group = self._create_group("⚡  Monitor Settings")
        monitor_layout = monitor_group.layout()

        self.cb_process = QCheckBox("Process Monitor  —  Track application launches and exits")
        self.cb_process.setChecked(True)
        monitor_layout.addWidget(self.cb_process)

        self.cb_file = QCheckBox("File Monitor  —  Watch for file system changes")
        self.cb_file.setChecked(True)
        monitor_layout.addWidget(self.cb_file)

        self.cb_system = QCheckBox("System Event Monitor  —  Read Windows Event Log")
        self.cb_system.setChecked(True)
        monitor_layout.addWidget(self.cb_system)

        # Poll intervals
        interval_row = QHBoxLayout()
        interval_row.setSpacing(16)

        interval_label = QLabel("Process poll interval (seconds):")
        interval_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; border: none;"
        )
        interval_row.addWidget(interval_label)

        self.process_interval = QSpinBox()
        self.process_interval.setRange(1, 30)
        self.process_interval.setValue(3)
        interval_row.addWidget(self.process_interval)

        interval_row.addStretch()
        monitor_layout.addLayout(interval_row)

        scroll_layout.addWidget(monitor_group)

        # ─── Application Tracking & Filtering ───────────────────
        app_group = self._create_group("🖥️  Application Tracking & Filtering")
        app_layout = app_group.layout()

        app_desc = QLabel(
            "Consolidate multiple processes and browser tabs into single, human-readable "
            "application sessions (Task Manager Apps style). Configure which applications to track."
        )
        app_desc.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; border: none;"
        )
        app_desc.setWordWrap(True)
        app_layout.addWidget(app_desc)

        # Filter mode selector
        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        mode_label = QLabel("Tracking Mode:")
        mode_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-weight: 600; font-size: 13px; border: none;"
        )
        mode_row.addWidget(mode_label)

        self.app_filter_mode_combo = QComboBox()
        self.app_filter_mode_combo.addItems([
            "Track all desktop applications (Recommended)",
            "Track only selected applications (Whitelist)",
            "Track all applications except excluded (Blacklist)",
        ])
        mode_row.addWidget(self.app_filter_mode_combo, 1)
        app_layout.addLayout(mode_row)

        # App list with checkboxes
        self.apps_list = QListWidget()
        self.apps_list.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"padding: 4px; }}"
            f"QListWidget::item {{ padding: 6px 8px; border-radius: 4px; "
            f"color: {COLORS['text_primary']}; }}"
            f"QListWidget::item:hover {{ background-color: {COLORS['bg_hover']}; }}"
        )
        self.apps_list.setMinimumHeight(180)
        app_layout.addWidget(self.apps_list)

        # Add custom app row
        add_app_row = QHBoxLayout()
        add_app_row.setSpacing(8)

        self.custom_app_input = QLineEdit()
        self.custom_app_input.setPlaceholderText("Enter application name or exe (e.g. 'Figma' or 'blender.exe')...")
        self.custom_app_input.returnPressed.connect(self._add_custom_app)
        add_app_row.addWidget(self.custom_app_input, 1)

        add_app_btn = QPushButton("+ Add App")
        add_app_btn.setProperty("class", "primary")
        add_app_btn.clicked.connect(self._add_custom_app)
        add_app_row.addWidget(add_app_btn)

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_apps_checked(True))
        add_app_row.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: self._set_all_apps_checked(False))
        add_app_row.addWidget(clear_all_btn)

        app_layout.addLayout(add_app_row)
        scroll_layout.addWidget(app_group)


        # ─── Monitored Paths ────────────────────────────────────
        paths_group = self._create_group("📁  Monitored Directories")
        paths_layout = paths_group.layout()

        paths_desc = QLabel(
            "Directories below are monitored for file changes. "
            "Add folders you want to track."
        )
        paths_desc.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; border: none;"
        )
        paths_desc.setWordWrap(True)
        paths_layout.addWidget(paths_desc)

        self.paths_list = QListWidget()
        self.paths_list.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"padding: 4px; }}"
            f"QListWidget::item {{ padding: 8px; border-radius: 4px; "
            f"color: {COLORS['text_primary']}; }}"
            f"QListWidget::item:selected {{ "
            f"background-color: {COLORS['accent_primary']}33; "
            f"color: {COLORS['text_primary']}; }}"
        )
        self.paths_list.setMinimumHeight(150)
        paths_layout.addWidget(self.paths_list)

        paths_btn_row = QHBoxLayout()
        paths_btn_row.setSpacing(8)

        add_path_btn = QPushButton("+ Add Directory")
        add_path_btn.setProperty("class", "primary")
        add_path_btn.clicked.connect(self._add_path)
        paths_btn_row.addWidget(add_path_btn)

        remove_path_btn = QPushButton("Remove Selected")
        remove_path_btn.setProperty("class", "danger")
        remove_path_btn.clicked.connect(self._remove_path)
        paths_btn_row.addWidget(remove_path_btn)

        paths_btn_row.addStretch()
        paths_layout.addLayout(paths_btn_row)

        scroll_layout.addWidget(paths_group)

        # ─── Data Management ────────────────────────────────────
        data_group = self._create_group("💾  Data Management")
        data_layout = data_group.layout()

        # Retention
        retention_row = QHBoxLayout()
        retention_row.setSpacing(12)

        ret_label = QLabel("Keep events for:")
        ret_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; border: none;"
        )
        retention_row.addWidget(ret_label)

        self.retention_days = QSpinBox()
        self.retention_days.setRange(1, 365)
        self.retention_days.setValue(30)
        self.retention_days.setSuffix(" days")
        retention_row.addWidget(self.retention_days)

        retention_row.addStretch()
        data_layout.addLayout(retention_row)

        # Event count
        self.event_count_label = QLabel("Total events stored: ...")
        self.event_count_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; border: none;"
        )
        data_layout.addWidget(self.event_count_label)

        # Data buttons
        data_btn_row = QHBoxLayout()
        data_btn_row.setSpacing(12)

        export_btn = QPushButton("📤  Export Data")
        export_btn.clicked.connect(self._export_data)
        data_btn_row.addWidget(export_btn)

        cleanup_btn = QPushButton("🗑️  Clean Old Events")
        cleanup_btn.clicked.connect(self._cleanup_data)
        data_btn_row.addWidget(cleanup_btn)

        migrate_btn = QPushButton("🔄  Normalize Legacy Events")
        migrate_btn.clicked.connect(self._migrate_data)
        data_btn_row.addWidget(migrate_btn)

        data_btn_row.addStretch()
        data_layout.addLayout(data_btn_row)


        scroll_layout.addWidget(data_group)

        # ─── About ──────────────────────────────────────────────
        about_group = self._create_group("ℹ️  About LOG NEST")
        about_layout = about_group.layout()

        about_header = QHBoxLayout()
        about_header.setSpacing(16)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(base_dir, "app_icon.png")
        if not os.path.exists(logo_path):
            logo_path = "app_icon.png"

        if os.path.exists(logo_path):
            about_logo = QLabel()
            about_pix = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            about_logo.setPixmap(about_pix)
            about_logo.setStyleSheet("border: none; background: transparent;")
            about_header.addWidget(about_logo)

        about_title_vbox = QVBoxLayout()
        about_title_vbox.setSpacing(4)
        about_title = QLabel("LOG NEST")
        about_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text_primary']}; border: none;")
        about_sub = QLabel("Version 1.0.0 — Offline Desktop Activity Tracker")
        about_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']}; border: none;")
        about_title_vbox.addWidget(about_title)
        about_title_vbox.addWidget(about_sub)
        about_header.addLayout(about_title_vbox)
        about_header.addStretch()

        about_layout.addLayout(about_header)
        about_layout.addSpacing(10)

        about_text = QLabel(
            "A privacy-focused Windows activity tracker that creates "
            "a searchable timeline of your computer's activity.\n\n"
            "All data is stored locally on your machine.\n"
            "No cloud connections. No telemetry. Your data stays yours.\n\n"
            "Future enhancements:\n"
            "  • Screenshot capture with OCR text extraction\n"
            "  • Natural-language AI search powered by local models\n"
            "  • Activity heatmaps and analytics"
        )
        about_text.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; "
            f"line-height: 1.6; border: none;"
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        scroll_layout.addWidget(about_group)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()

        save_btn = QPushButton("💾  Save Settings")
        save_btn.setProperty("class", "primary")
        save_btn.setStyleSheet(
            f"QPushButton {{ font-size: 14px; padding: 12px 32px; "
            f"background-color: {COLORS['accent_primary']}; color: white; "
            f"border: none; border-radius: 10px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: #7B73FF; }}"
        )
        save_btn.clicked.connect(self._save_settings)
        save_row.addWidget(save_btn)

        scroll_layout.addLayout(save_row)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

    def _create_group(self, title):
        """Create a styled group box."""
        group = QGroupBox(title)
        group.setStyleSheet(
            f"QGroupBox {{ "
            f"  background-color: {COLORS['bg_card']}; "
            f"  border: 1px solid {COLORS['border']}; "
            f"  border-radius: 12px; "
            f"  margin-top: 20px; "
            f"  padding: 24px 20px 20px 20px; "
            f"  font-size: 15px; "
            f"  font-weight: 600; "
            f"  color: {COLORS['text_primary']}; "
            f"}} "
            f"QGroupBox::title {{ "
            f"  subcontrol-origin: margin; "
            f"  subcontrol-position: top left; "
            f"  padding: 4px 12px; "
            f"}}"
        )
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        return group

    def _load_settings(self):
        """Load saved settings from database."""
        db = self.db

        self.cb_process.setChecked(
            db.get_setting("monitor_process_enabled", "true") == "true"
        )
        self.cb_file.setChecked(
            db.get_setting("monitor_file_enabled", "true") == "true"
        )
        self.cb_system.setChecked(
            db.get_setting("monitor_system_enabled", "true") == "true"
        )

        interval = db.get_setting("process_poll_interval", "3")
        self.process_interval.setValue(int(interval))

        retention = db.get_setting("retention_days", "30")
        self.retention_days.setValue(int(retention))

        # Load paths
        self._refresh_paths()

        # Load application filters
        self._load_app_filters()

        # Event count
        count = db.get_event_count()
        self.event_count_label.setText(f"Total events stored: {count:,}")

    def _load_app_filters(self):
        """Load and populate application filtering list."""
        from src.utils.app_metadata import KNOWN_APPLICATIONS

        filter_cfg = self.db.get_app_filter_settings()
        mode = filter_cfg.get("mode", "all")
        tracked = {a.lower() for a in filter_cfg.get("tracked", [])}
        excluded = {a.lower() for a in filter_cfg.get("excluded", [])}

        mode_indices = {"all": 0, "include": 1, "exclude": 2}
        self.app_filter_mode_combo.setCurrentIndex(mode_indices.get(mode, 0))

        # Collect candidate application display names
        candidate_apps = {}
        for exe, meta in KNOWN_APPLICATIONS.items():
            candidate_apps[meta["name"]] = exe

        # Include any tracked or excluded custom apps
        for item in filter_cfg.get("tracked", []) + filter_cfg.get("excluded", []):
            if item and item not in candidate_apps:
                candidate_apps[item] = item

        self.apps_list.clear()
        for name in sorted(candidate_apps.keys()):
            exe_hint = candidate_apps[name]
            item = QListWidgetItem(f"📱  {name}  ({exe_hint})")
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # Determine check state based on mode
            if mode == "include":
                checked = name.lower() in tracked
            elif mode == "exclude":
                checked = name.lower() in excluded
            else:
                checked = True

            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.apps_list.addItem(item)

    def _set_all_apps_checked(self, checked: bool):
        """Set check state of all apps in list."""
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.apps_list.count()):
            self.apps_list.item(i).setCheckState(state)

    @Slot()
    def _add_custom_app(self):
        """Add a custom application to the tracking list."""
        app_name = self.custom_app_input.text().strip()
        if not app_name:
            return

        # Check for duplicates
        for i in range(self.apps_list.count()):
            if self.apps_list.item(i).data(Qt.UserRole).lower() == app_name.lower():
                self.apps_list.item(i).setCheckState(Qt.Checked)
                self.custom_app_input.clear()
                return

        item = QListWidgetItem(f"📱  {app_name}")
        item.setData(Qt.UserRole, app_name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        self.apps_list.addItem(item)
        self.custom_app_input.clear()

    def _refresh_paths(self):
        """Refresh the monitored paths list."""
        self.paths_list.clear()
        paths = self.db.get_monitored_paths()
        for p in paths:
            item = QListWidgetItem(
                f"{'📂' if p['recursive'] else '📁'}  {p['path']}"
            )
            item.setData(Qt.UserRole, p["id"])
            self.paths_list.addItem(item)

    @Slot()
    def _add_path(self):
        """Add a new monitored directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Monitor"
        )
        if path:
            self.db.add_monitored_path(path, recursive=False)
            self._refresh_paths()
            self.paths_changed.emit()

    @Slot()
    def _remove_path(self):
        """Remove the selected monitored directory."""
        current = self.paths_list.currentItem()
        if current:
            path_id = current.data(Qt.UserRole)
            self.db.remove_monitored_path(path_id)
            self._refresh_paths()
            self.paths_changed.emit()

    @Slot()
    def _save_settings(self):
        """Save all settings to database."""
        db = self.db

        db.set_setting("monitor_process_enabled",
                        "true" if self.cb_process.isChecked() else "false")
        db.set_setting("monitor_file_enabled",
                        "true" if self.cb_file.isChecked() else "false")
        db.set_setting("monitor_system_enabled",
                        "true" if self.cb_system.isChecked() else "false")
        db.set_setting("process_poll_interval",
                        str(self.process_interval.value()))
        db.set_setting("retention_days",
                        str(self.retention_days.value()))

        # Save application filtering settings
        mode_keys = ["all", "include", "exclude"]
        mode = mode_keys[self.app_filter_mode_combo.currentIndex()]

        checked_apps = []
        for i in range(self.apps_list.count()):
            item = self.apps_list.item(i)
            if item.checkState() == Qt.Checked:
                checked_apps.append(item.data(Qt.UserRole))

        if mode == "include":
            db.set_app_filter_settings(mode="include", tracked=checked_apps, excluded=[])
        elif mode == "exclude":
            db.set_app_filter_settings(mode="exclude", tracked=[], excluded=checked_apps)
        else:
            db.set_app_filter_settings(mode="all", tracked=checked_apps, excluded=[])

        self.monitors_changed.emit()

        QMessageBox.information(
            self, "Settings Saved",
            "Settings have been saved successfully.\n"
            "Application tracking filters are now active!"
        )

    @Slot()
    def _migrate_data(self):
        """Safely normalize legacy process events in the database."""
        reply = QMessageBox.question(
            self, "Normalize Events",
            "This will convert older raw process events (like 'msedge.exe started') "
            "into clean, application-level events (like 'Microsoft Edge opened') "
            "without modifying raw database IDs or timestamps.\n\n"
            "Proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                conn = self.db._get_conn()
                cursor = conn.cursor()
                self.db._migrate_legacy_events(cursor)
                conn.commit()
                count = self.db.get_event_count()
                self.event_count_label.setText(f"Total events stored: {count:,}")
                QMessageBox.information(
                    self, "Migration Complete",
                    "Database events have been normalized safely."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Migration Error",
                    f"Error normalizing events: {e}"
                )


    @Slot()
    def _export_data(self):
        """Export events to a JSON file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Events", "lognest_export.json",
            "JSON Files (*.json)"
        )
        if filepath:
            try:
                count = self.db.export_events(filepath)
                QMessageBox.information(
                    self, "Export Complete",
                    f"Exported {count:,} events to:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error",
                    f"Failed to export: {e}"
                )

    @Slot()
    def _cleanup_data(self):
        """Delete old events."""
        days = self.retention_days.value()
        reply = QMessageBox.question(
            self, "Confirm Cleanup",
            f"Delete all events older than {days} days?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                deleted = self.db.cleanup_old_events(days)
                count = self.db.get_event_count()
                self.event_count_label.setText(
                    f"Total events stored: {count:,}"
                )
                QMessageBox.information(
                    self, "Cleanup Complete",
                    f"Deleted {deleted:,} old events."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Cleanup Error",
                    f"Failed to cleanup: {e}"
                )
