"""
LOG NEST - Application Metadata and Classification
Identifies user-facing applications, extracts human-readable names,
detects subprocess roles (renderers, GPUs, utilities), and filters system noise.
"""

import os
import re
import logging
import ctypes
import ctypes.wintypes
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Tuple, Any
import psutil

logger = logging.getLogger(__name__)

# Chromium and Electron subprocess arguments
CHROMIUM_SUBPROCESS_PATTERNS = [
    "--type=renderer",
    "--type=gpu-process",
    "--type=utility",
    "--type=crashpad-handler",
    "--type=extensionHost",
    "--type=watcher",
    "--type=broker",
    "--type=service",
    "--type=ppapi",
    "--type=network.mojom",
    "--type=audio.mojom",
    "--type=storage.mojom",
]

# Curated dictionary of common desktop applications for instant, clean recognition
KNOWN_APPLICATIONS = {
    "msedge.exe": {"name": "Microsoft Edge", "id": "microsoft_edge", "category": "Browser"},
    "chrome.exe": {"name": "Google Chrome", "id": "google_chrome", "category": "Browser"},
    "firefox.exe": {"name": "Mozilla Firefox", "id": "firefox", "category": "Browser"},
    "brave.exe": {"name": "Brave Browser", "id": "brave", "category": "Browser"},
    "opera.exe": {"name": "Opera", "id": "opera", "category": "Browser"},
    "code.exe": {"name": "Visual Studio Code", "id": "vscode", "category": "Developer Tool"},
    "opencode.exe": {"name": "OpenCode", "id": "opencode", "category": "Developer Tool"},
    "antigravity ide.exe": {"name": "Antigravity IDE", "id": "antigravity_ide", "category": "Developer Tool"},
    "notepad.exe": {"name": "Notepad", "id": "notepad", "category": "Productivity"},
    "notepad++.exe": {"name": "Notepad++", "id": "notepad_plus_plus", "category": "Developer Tool"},
    "calc.exe": {"name": "Calculator", "id": "calculator", "category": "Utility"},
    "calculatorapp.exe": {"name": "Calculator", "id": "calculator", "category": "Utility"},
    "mspaint.exe": {"name": "Paint", "id": "paint", "category": "Creative"},
    "explorer.exe": {"name": "Windows Explorer", "id": "explorer", "category": "System"},
    "spotify.exe": {"name": "Spotify", "id": "spotify", "category": "Media"},
    "discord.exe": {"name": "Discord", "id": "discord", "category": "Communication"},
    "slack.exe": {"name": "Slack", "id": "slack", "category": "Communication"},
    "teams.exe": {"name": "Microsoft Teams", "id": "teams", "category": "Communication"},
    "ms-teams.exe": {"name": "Microsoft Teams", "id": "teams", "category": "Communication"},
    "steam.exe": {"name": "Steam", "id": "steam", "category": "Gaming"},
    "steamwebhelper.exe": {"name": "Steam", "id": "steam", "category": "Gaming"},
    "windowsterminal.exe": {"name": "Windows Terminal", "id": "windows_terminal", "category": "Developer Tool"},
    "wt.exe": {"name": "Windows Terminal", "id": "windows_terminal", "category": "Developer Tool"},
    "powershell.exe": {"name": "PowerShell", "id": "powershell", "category": "Developer Tool"},
    "pwsh.exe": {"name": "PowerShell Core", "id": "powershell_core", "category": "Developer Tool"},
    "cmd.exe": {"name": "Command Prompt", "id": "cmd", "category": "Developer Tool"},
    "taskmgr.exe": {"name": "Task Manager", "id": "task_manager", "category": "System"},
    "devenv.exe": {"name": "Visual Studio", "id": "visual_studio", "category": "Developer Tool"},
    "pycharm64.exe": {"name": "PyCharm", "id": "pycharm", "category": "Developer Tool"},
    "idea64.exe": {"name": "IntelliJ IDEA", "id": "intellij", "category": "Developer Tool"},
    "vlc.exe": {"name": "VLC Media Player", "id": "vlc", "category": "Media"},
    "obs64.exe": {"name": "OBS Studio", "id": "obs_studio", "category": "Media"},
    "zoom.exe": {"name": "Zoom", "id": "zoom", "category": "Communication"},
    "word.exe": {"name": "Microsoft Word", "id": "ms_word", "category": "Productivity"},
    "winword.exe": {"name": "Microsoft Word", "id": "ms_word", "category": "Productivity"},
    "excel.exe": {"name": "Microsoft Excel", "id": "ms_excel", "category": "Productivity"},
    "powerpnt.exe": {"name": "Microsoft PowerPoint", "id": "ms_powerpoint", "category": "Productivity"},
    "outlook.exe": {"name": "Microsoft Outlook", "id": "ms_outlook", "category": "Communication"},
    "onenote.exe": {"name": "Microsoft OneNote", "id": "ms_onenote", "category": "Productivity"},
    "telegram.exe": {"name": "Telegram", "id": "telegram", "category": "Communication"},
    "blender.exe": {"name": "Blender", "id": "blender", "category": "Creative"},
    "gimp.exe": {"name": "GIMP", "id": "gimp", "category": "Creative"},
    "figma.exe": {"name": "Figma", "id": "figma", "category": "Creative"},
    "postman.exe": {"name": "Postman", "id": "postman", "category": "Developer Tool"},
    "git-kraken.exe": {"name": "GitKraken", "id": "gitkraken", "category": "Developer Tool"},
}

# Processes that should never be tracked as standalone user applications
SYSTEM_AND_HELPER_EXES = {
    # System core and session 0 processes
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "fontdrvhost.exe",
    "dwm.exe", "conhost.exe", "winlogon.exe", "lsaiso.exe",
    "memory compression", "system idle process", "secure system",
    "ntoskrnl.exe", "spoolsv.exe", "searchindexer.exe",
    "msdtc.exe", "dllhost.exe", "wudfhost.exe", "audiodg.exe",
    "runtimebroker.exe", "sihost.exe", "ctfmon.exe", "dashost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe",
    "textinputhost.exe", "shellexperiencehost.exe",
    "widgetservice.exe", "gameinputsvc.exe",
    "securityhealthservice.exe", "sgrmbroker.exe",
    "crashpad_handler.exe", "msedgewebview2.exe",
    "microsoftedgeupdate.exe", "edge_crashpad_handler.exe",
    "googleupdate.exe", "taskhostw.exe", "wermgr.exe",
    "compattelrunner.exe", "smartscreen.exe", "backgroundtaskhost.exe",
    "applicationframehost.exe", "useroobebroker.exe", "systemsettingsbroker.exe",
    "openconsole.exe", "searchprotocolhost.exe", "searchfilterhost.exe",
    "aggregatorhost.exe", "presentationfontcache.exe", "sppsvc.exe",
    "msmpeng.exe", "nissrv.exe", "mpdefendercoreservice.exe",
    "speechruntime.exe", "gamingservices.exe", "gamingservicesnet.exe",
    "memcompression", "searchapp.exe", "ravbg64.exe", "officeclicktorun.exe",
    "smartscreenps.exe", "securityhealthsystray.exe",
}



@dataclass
class AppInfo:
    """Normalized application and process classification metadata."""
    app_id: str
    display_name: str
    exe_name: str
    exe_path: str
    is_user_app: bool
    is_subprocess: bool
    subprocess_role: str = ""
    category: str = "Application"


def get_file_version_metadata(exe_path: str) -> Optional[str]:
    """Extract FileDescription or ProductName from Windows PE version resource."""
    if not exe_path or not os.path.exists(exe_path):
        return None
    try:
        import win32api
        langs = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")
        translations = []
        if langs:
            translations.extend(langs)
        # Add common fallbacks: US English Unicode, US English Multilingual, Neutral
        translations.extend([(0x0409, 0x04B0), (0x0409, 0x04E4), (0x0000, 0x04B0)])

        for lang, codepage in translations:
            str_info_path = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\"
            for key in ["FileDescription", "ProductName"]:
                try:
                    val = win32api.GetFileVersionInfo(exe_path, str_info_path + key)
                    if val and isinstance(val, str) and val.strip():
                        cleaned = val.strip()
                        # Avoid generic strings
                        if cleaned.lower() not in ("application", "setup", "launcher"):
                            return cleaned
                except Exception:
                    pass
    except Exception:
        pass
    return None


def detect_subprocess_role(exe_name: str, cmdline: List[str]) -> Tuple[bool, str]:
    """
    Check if a process is an internal subprocess (renderer, GPU, utility, etc.).
    Returns (is_subprocess, role_name).
    """
    cmd_str = " ".join(cmdline).lower()

    for pat in CHROMIUM_SUBPROCESS_PATTERNS:
        if pat.lower() in cmd_str:
            role = pat.split("=")[-1]
            return True, role

    if "-contentproc" in cmd_str:
        return True, "content-process"

    exe_lower = exe_name.lower()
    if "crashpad" in exe_lower or "crashpad_handler" in cmd_str:
        return True, "crash-handler"

    if exe_lower == "msedgewebview2.exe":
        return True, "webview"

    if exe_lower in ("conhost.exe", "openconsole.exe"):
        return True, "console-host"

    return False, ""


def is_system_or_background_service(name: str, exe_path: str, session_id: Optional[int], file_desc: Optional[str] = None) -> bool:
    """Determine if a process is a Windows system service or background OS host."""
    name_lower = name.lower().strip()
    if name_lower in SYSTEM_AND_HELPER_EXES:
        return True

    # Generic service binary patterns
    if name_lower.endswith("service.exe") or name_lower.endswith("svc.exe"):
        return True
    if any(prefix in name_lower for prefix in ("service", "helper", "host", "broker", "daemon")):
        if name_lower not in ("windowsterminal.exe", "powershell.exe", "cmd.exe"):
            # Check if it's not a known primary desktop app
            if name_lower not in KNOWN_APPLICATIONS:
                return True

    # Session 0 is reserved strictly for non-interactive system services
    if session_id == 0:
        return True

    # Check file description for background service indicators
    if file_desc:
        desc_lower = file_desc.lower()
        if any(term in desc_lower for term in ("service", "daemon", "filter host", "protocol host", "sync engine", "telemetry", "background process", "click-to-run", "sync service")):
            if name_lower not in KNOWN_APPLICATIONS:
                return True


    # Exclude system folders unless explicitly in known desktop apps
    if exe_path:
        norm_path = exe_path.lower().replace("/", "\\")
        windir = os.environ.get("SystemRoot", "C:\\Windows").lower()
        sys32 = os.path.join(windir, "system32")
        syswow = os.path.join(windir, "syswow64")

        # Allow specific legitimate user utilities located in system32
        allowed_in_sys32 = {"notepad.exe", "calc.exe", "mspaint.exe", "explorer.exe", "taskmgr.exe", "cmd.exe"}
        if (norm_path.startswith(sys32) or norm_path.startswith(syswow)) and name_lower not in allowed_in_sys32:
            return True

    return False



def resolve_application_info(
    name: str,
    exe_path: str = "",
    cmdline: Optional[List[str]] = None,
    session_id: Optional[int] = None
) -> AppInfo:
    """
    Produce normalized application identification and classify user vs subprocess.
    """
    name_clean = (name or "").strip()
    name_lower = name_clean.lower()
    cmdline = cmdline or []

    # 1. Detect if it's an internal subprocess
    is_sub, sub_role = detect_subprocess_role(name_clean, cmdline)

    # Resolve display name and file description
    file_desc = None
    if name_lower in KNOWN_APPLICATIONS:
        app_meta = KNOWN_APPLICATIONS[name_lower]
        display_name = app_meta["name"]
        app_id = app_meta["id"]
        category = app_meta.get("category", "Application")
    else:
        file_desc = get_file_version_metadata(exe_path)
        if file_desc:
            display_name = file_desc
        else:
            base = os.path.splitext(name_clean)[0]
            display_name = base.replace("_", " ").replace("-", " ").title()

        # Sanitize app_id
        app_id = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
        category = "Application"

    # 2. Check system/background service status
    is_sys = is_system_or_background_service(name_clean, exe_path, session_id, file_desc)

    # Edge WebView2 used by Windows Search/Widgets shouldn't masquerade as Microsoft Edge
    if name_lower == "msedgewebview2.exe":
        display_name = "Edge WebView2"
        app_id = "edge_webview2"
        is_sub = True

    # User-facing application check:
    # A process is a user app if it's not a system service/helper and not a pure internal subprocess
    is_user_app = not is_sys and not is_sub

    return AppInfo(
        app_id=app_id,
        display_name=display_name,
        exe_name=name_clean,
        exe_path=exe_path,
        is_user_app=is_user_app,
        is_subprocess=is_sub,
        subprocess_role=sub_role,
        category=category,
    )


def get_visible_windows_by_pid() -> Dict[int, List[Dict]]:
    """
    Safely enumerate top-level, interactive desktop windows grouped by process PID.
    Filters out invisible, 0-sized, tooltip, and internal IME windows.
    """
    user32 = ctypes.windll.user32
    windows_by_pid: Dict[int, List[Dict]] = {}

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def enum_cb(hwnd, lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            # Filter zero-sized and tiny utility windows
            if w <= 10 or h <= 10:
                return True

            title_len = user32.GetWindowTextLengthW(hwnd)
            if title_len == 0:
                return True

            buff = ctypes.create_unicode_buffer(title_len + 1)
            user32.GetWindowTextW(hwnd, buff, title_len + 1)
            title = buff.value.strip()

            # Ignore internal IME / system handles
            if title in ("MSCTFIME UI", "Default IME"):
                return True

            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value > 0:
                windows_by_pid.setdefault(pid.value, []).append({
                    "hwnd": hwnd,
                    "title": title,
                    "width": w,
                    "height": h,
                })
        except Exception:
            pass
        return True

    cb = WNDENUMPROC(enum_cb)

    # Attempt to open active input desktop, fallback to standard EnumWindows
    DESKTOP_ENUMERATE = 0x0040
    DESKTOP_READOBJECTS = 0x0001
    h_desk = None
    try:
        h_desk = user32.OpenInputDesktop(0, False, DESKTOP_ENUMERATE | DESKTOP_READOBJECTS)
    except Exception:
        pass

    if h_desk:
        try:
            user32.EnumDesktopWindows(h_desk, cb, 0)
        except Exception:
            user32.EnumWindows(cb, 0)
        finally:
            user32.CloseDesktop(h_desk)
    else:
        try:
            user32.EnumWindows(cb, 0)
        except Exception:
            pass

    return windows_by_pid


def get_process_session_id(pid: int) -> Optional[int]:
    """Get the Windows Session ID for a process using kernel32.ProcessIdToSessionId."""
    try:
        kernel32 = ctypes.windll.kernel32
        sess = ctypes.wintypes.DWORD()
        if kernel32.ProcessIdToSessionId(ctypes.wintypes.DWORD(pid), ctypes.byref(sess)):
            return sess.value
    except Exception:
        pass
    return None


def is_taskbar_window(hwnd: int) -> Tuple[bool, str]:
    """
    Determine if a top-level window is displayed as a running application on the Windows taskbar.
    Applies standard Windows Shell rules:
    - Must be visible
    - Must not be cloaked (virtual desktop hidden, suspended UWP)
    - Tool windows excluded unless WS_EX_APPWINDOW is set
    - Owned windows excluded unless WS_EX_APPWINDOW is set
    - Non-empty client rect or iconic (minimized)
    - Non-empty meaningful title (filters internal IME / system windows)
    """
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    if not user32.IsWindowVisible(hwnd):
        return False, ""

    # Check if cloaked (Windows 10/11 modern apps or minimized to background)
    cloaked = ctypes.wintypes.DWORD()
    hr = dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))  # 14 = DWMWA_CLOAKED
    if hr == 0 and cloaked.value != 0:
        return False, ""

    ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
        return False, ""

    owner = user32.GetWindow(hwnd, 4)  # GW_OWNER
    if owner != 0 and not (ex_style & WS_EX_APPWINDOW):
        return False, ""

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if rect.right <= rect.left or rect.bottom <= rect.top:
        if not user32.IsIconic(hwnd):
            return False, ""

    title_len = user32.GetWindowTextLengthW(hwnd)
    if title_len == 0:
        return False, ""

    buff = ctypes.create_unicode_buffer(title_len + 1)
    user32.GetWindowTextW(hwnd, buff, title_len + 1)
    title = buff.value.strip()
    if not title or title in ("Program Manager", "MSCTFIME UI", "Default IME"):
        return False, ""

    return True, title


def resolve_window_pid(hwnd: int) -> int:
    """Resolve the real application PID, unwrapping ApplicationFrameHost for UWP apps."""
    user32 = ctypes.windll.user32
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        proc = psutil.Process(pid.value)
        if proc.name().lower() == "applicationframehost.exe":
            child_hwnd = user32.FindWindowExW(hwnd, 0, "Windows.UI.Core.CoreWindow", None)
            if child_hwnd:
                child_pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(child_hwnd, ctypes.byref(child_pid))
                if child_pid.value > 0:
                    return child_pid.value
    except Exception:
        pass
    return pid.value


def get_application_user_model_id(pid: int) -> Optional[str]:
    """Retrieve AppUserModelID for a process if available via kernel32."""
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            try:
                length = ctypes.wintypes.UINT(0)
                ret = kernel32.GetApplicationUserModelId(h, ctypes.byref(length), None)
                if ret == 122 and length.value > 0:  # ERROR_INSUFFICIENT_BUFFER
                    buff = ctypes.create_unicode_buffer(length.value)
                    if kernel32.GetApplicationUserModelId(h, ctypes.byref(length), buff) == 0:
                        return buff.value
            finally:
                kernel32.CloseHandle(h)
    except Exception:
        pass
    return None


def get_running_taskbar_applications() -> Dict[str, Dict[str, Any]]:
    """
    Enumerate applications visible as running apps on the Windows taskbar.
    Groups windows by logical application identity and resolves executable metadata.
    """
    user32 = ctypes.windll.user32
    taskbar_windows = []

    def enum_cb(hwnd, lparam):
        ok, title = is_taskbar_window(hwnd)
        if ok:
            pid = resolve_window_pid(hwnd)
            taskbar_windows.append((hwnd, pid, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    h_desk = None
    try:
        h_desk = user32.OpenInputDesktop(0, False, 0x0040 | 0x0001)
    except Exception:
        pass

    if h_desk:
        try:
            user32.EnumDesktopWindows(h_desk, WNDENUMPROC(enum_cb), 0)
        finally:
            user32.CloseDesktop(h_desk)
    else:
        try:
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        except Exception:
            pass

    apps: Dict[str, Dict[str, Any]] = {}
    for hwnd, pid, title in taskbar_windows:
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            exe = proc.exe()
            cmdline = proc.cmdline()
            session_id = get_process_session_id(pid)

            app_info = resolve_application_info(name, exe, cmdline, session_id)
            if not app_info.is_user_app:
                continue

            aid = app_info.app_id
            aumid = get_application_user_model_id(pid)

            if aid not in apps:
                apps[aid] = {
                    "app_id": aid,
                    "display_name": app_info.display_name,
                    "category": app_info.category,
                    "main_pid": pid,
                    "exe_path": exe,
                    "pids": {pid},
                    "windows": [(hwnd, title)],
                    "app_info": app_info,
                    "aumid": aumid,
                    "username": proc.username() if hasattr(proc, "username") else "",
                }
            else:
                apps[aid]["windows"].append((hwnd, title))
                apps[aid]["pids"].add(pid)
        except Exception:
            continue

    return apps

