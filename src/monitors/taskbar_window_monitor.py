"""Live taskbar-window discovery and per-window observed lifetimes."""
import ctypes
from ctypes import wintypes
import time
import psutil
from PySide6.QtCore import QThread, Signal
from src.utils.app_metadata import is_taskbar_window, resolve_window_pid, resolve_application_info


def enumerate_taskbar_windows():
    """Return actual Shell-eligible top-level windows, including minimized ones."""
    user = ctypes.windll.user32
    user.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetWindow.restype = wintypes.HWND
    user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsIconic.argtypes = [wintypes.HWND]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    ctypes.windll.dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
    windows = []
    process_cache = {}
    def collect(hwnd, _):
        try:
            eligible, title = is_taskbar_window(hwnd)
            if not eligible:
                return True
            name_buffer = ctypes.create_unicode_buffer(256)
            user.GetClassNameW(hwnd, name_buffer, 256)
            if name_buffer.value in {'Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd'}:
                return True
            style = user.GetWindowLongW(hwnd, -20)
            if style & 0x08000000 and not style & 0x00040000:  # NOACTIVATE without APPWINDOW
                return True
            pid = resolve_window_pid(hwnd)
            if pid not in process_cache:
                proc = psutil.Process(pid)
                try: exe = proc.exe()
                except psutil.AccessDenied: exe = ''
                try:
                    process_name = proc.name()
                except psutil.AccessDenied:
                    process_name = title
                try:
                    created = proc.create_time()
                except psutil.AccessDenied:
                    created = 0
                info = resolve_application_info(process_name, exe, [])
                process_cache[pid] = dict(pid=pid, process_started=created,
                    app_id=info.app_id, app_name=info.display_name, exe_path=exe)
            windows.append(dict(process_cache[pid], hwnd=int(hwnd), title=title))
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
        return True
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    if not user.EnumWindows(callback_type(collect), 0):
        raise ctypes.WinError()
    return windows


class WindowLifetimes:
    """Use window identity, never process age or accumulated foreground time."""
    def __init__(self):
        self._windows = {}
        self._initialized = False

    def reconcile(self, snapshot, now=None):
        now = time.monotonic() if now is None else now
        current = {}
        for window in snapshot:
            key = (window['hwnd'], window['pid'], window['process_started'])
            old = self._windows.get(key)
            current[key] = dict(window, key=key,
                observed_at=old['observed_at'] if old else now,
                preexisting=old['preexisting'] if old else not self._initialized)
        # Existing cards keep their order even when foreground/Z-order changes.
        ordered = [key for key in self._windows if key in current]
        ordered.extend(key for key in current if key not in self._windows)
        self._windows = {key: current[key] for key in ordered}
        self._initialized = True
        return list(self._windows.values())


class TaskbarWindowMonitor(QThread):
    windows_changed = Signal(list)
    error_occurred = Signal(str)

    def run(self):
        lifetimes = WindowLifetimes()
        previous = None
        while not self.isInterruptionRequested():
            try:
                snapshot = lifetimes.reconcile(enumerate_taskbar_windows())
                if snapshot != previous:
                    self.windows_changed.emit(snapshot)
                    previous = snapshot
            except Exception as exc:
                self.error_occurred.emit(f'Taskbar windows: {exc}')
                if previous != []:
                    self.windows_changed.emit([])
                previous = []
            for _ in range(10):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)

    def stop(self):
        self.requestInterruption()
        self.wait(3000)
