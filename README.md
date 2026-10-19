# LOG NEST 🪺

**A privacy-focused Windows desktop application that tracks computer activity and creates a searchable timeline.**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![SQLite](https://img.shields.io/badge/Storage-SQLite-orange)
![Windows](https://img.shields.io/badge/Platform-Windows-lightblue)

---

## Features

### 🔷 Activity Monitoring
- **Process Tracking** — Detects application launches and exits in real-time
- **File System Monitoring** — Watches configured directories for file changes (created, modified, deleted, moved)
- **Windows Event Log** — Captures system errors, warnings, and crash reports from Windows Event Log
- **Crash Detection** — Identifies application crashes via Windows Error Reporting

### 🌿 Digital Wellbeing (Android-Style for Windows)
- **Real-Time PC Clock Synchronization** — Live sync with Windows system clock and date
- **Circular Screen Time Donut Chart** — Android-inspired ring chart showing today's screen time and app distribution
- **Live Active Application Tracking** — Foreground window detection with real-time focus stopwatch
- **App Usage Breakdown** — Daily screen time, launch counts, and percentage per app
- **App Daily Limits & Timers** — Configurable daily usage caps with tray warnings and alerts
- **Focus Mode & Bedtime Schedule** — Distraction-free focus timer and wind-down reminders
- **Idle Screen Timeout** — Automatically pauses screen time tracking when user is idle or away

### 📊 Dashboard
- Live statistics cards (total events, active processes, file changes, errors)
- Hourly activity bar chart
- Category breakdown with progress bars
- Recent events feed with auto-refresh

### 📋 Timeline
- Chronological event list with color-coded cards
- Filters: category, severity, date range
- Quick-filter text search
- Pagination for large datasets
- Auto-refresh toggle
- Click any event to see full details + surrounding context (±5 min)

### 🔍 Search
- Full-text search powered by SQLite FTS5
- Highlighted search results
- Category and date range filters
- "Before/After" context view for any event

### ⚙️ Settings
- Enable/disable individual monitors
- Manage monitored directories
- Data retention policy
- Export events to JSON
- Clean up old events

### 🔒 Privacy
- **100% local** — all data stored in `~/.lognest/lognest.db`
- **No cloud connections** — no telemetry, no external APIs
- **You control your data** — export, delete, or set retention policies

---

## Installation

### Prerequisites
- **Python 3.11+** installed on Windows
- **pip** package manager

### Quick Launch (.EXE Application)
You can launch **LOG NEST** directly as a Windows executable without needing Python commands:
- **Desktop Shortcut**: Double-click the **LOG NEST** shortcut on your Windows Desktop.
- **Root Launcher**: Double-click [Launch_LogNest.bat](file:///d:/LOG_NEST/Launch_LogNest.bat) or [LOG NEST.lnk](file:///d:/LOG_NEST/LOG%20NEST.lnk) in `D:\LOG_NEST\`.
- **Direct Executable**: Run [LogNest.exe](file:///d:/LOG_NEST/dist/LogNest/LogNest.exe) located in `D:\LOG_NEST\dist\LogNest\LogNest.exe`.

---

## Developer / Source Setup

1. **Clone or download** this repository:
   ```bash
   cd LOG_NEST
   ```

2. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Run from source**:
   ```bash
   python main.py
   ```

### Dependencies
| Package | Purpose |
|---------|---------|
| `PySide6` | Qt-based GUI framework |
| `psutil` | Cross-platform process monitoring |
| `watchdog` | File system event monitoring |
| `pywin32` | Windows Event Log access |
| `pyinstaller` | Standalone Windows executable bundling |

---

## Usage

### First Launch
1. Launch via `LogNest.exe`, `LOG NEST.lnk`, or `python main.py`.
2. The app opens with the **Dashboard** view.
3. Monitors start automatically in the background.
4. The app minimizes to the **system tray** when you close the window.
5. Double-click the tray icon to restore the window.

### Dashboard
View live statistics about your system activity. Cards auto-update every 5 seconds.

### Timeline
Browse all events chronologically. Use the filter bar to narrow down by:
- **Category**: Application, FileSystem, System, Crash
- **Severity**: info, warning, error, critical
- **Date range**: From/To date pickers

Click any event card to open the **detail dialog** with:
- Full event metadata
- Events that occurred ±5 minutes before/after (context view)

### Search
Type any keyword to search across all event titles, descriptions, and sources.
Results are ranked by relevance with highlighted matches.

### Settings
- Add/remove directories to monitor for file changes
- Toggle individual monitors on/off
- Set data retention period
- Export all events to JSON
- Clean up old events

---

## Data Storage

All data is stored locally at:
```
%USERPROFILE%\.lognest\
├── lognest.db          # SQLite database (events, settings, paths)
└── logs\               # Application log files
    └── lognest_YYYYMMDD.log
```

---

## Architecture

```
LOG_NEST/
├── main.py                          # Entry point
├── requirements.txt                 # Python dependencies
├── src/
│   ├── database.py                  # SQLite + FTS5 database manager
│   ├── monitors/
│   │   ├── process_monitor.py       # psutil-based process tracker
│   │   ├── file_monitor.py          # watchdog file system watcher
│   │   ├── system_event_monitor.py  # Windows Event Log reader
│   │   └── monitor_manager.py       # Coordinator for all monitors
│   ├── ui/
│   │   ├── main_window.py           # Main window + sidebar + tray
│   │   ├── dashboard_page.py        # Dashboard stats & charts
│   │   ├── timeline_page.py         # Event timeline + filters
│   │   ├── search_page.py           # Full-text search
│   │   ├── settings_page.py         # Settings & data management
│   │   ├── widgets.py               # Custom UI components
│   │   └── theme.py                 # Dark theme & color palette
│   └── utils/
│       └── helpers.py               # Utility functions
```

---

## Future Enhancements

These features are planned but not yet implemented:

- 📸 **Screenshot Capture** — Periodic screenshots with configurable intervals
- 🔤 **OCR Text Extraction** — Extract text from screenshots using Tesseract/Windows OCR
- 🤖 **AI-Powered Search** — Natural-language queries powered by local LLM models
- 📈 **Activity Heatmaps** — Visual heatmaps showing usage patterns
- 🔔 **Custom Alerts** — Set rules to trigger notifications on specific events

---

## License

This project is for personal use. All data stays on your machine.
