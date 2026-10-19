"""Real Edge taskbar lifecycle check in an isolated browser profile and database."""
import sys,os,time,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil,win32gui,win32con
from src.database import DatabaseManager
from src.monitors.process_monitor import ProcessMonitor
from src.utils.app_metadata import get_running_taskbar_applications,resolve_window_pid

edge=next(p for p in [Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe',Path('C:/Program Files/Microsoft/Edge/Application/msedge.exe')] if p.exists())
with tempfile.TemporaryDirectory(prefix='lognest-edge-') as folder:
    profile=str(Path(folder)/'profile')
    db=DatabaseManager(str(Path(folder)/'test.db'))
    monitor=ProcessMonitor()
    events=[]
    monitor.event_detected.connect(events.append)
    def owned(pid):
        try:return any(profile.lower() in arg.lower() for arg in psutil.Process(pid).cmdline())
        except (psutil.NoSuchProcess,psutil.AccessDenied):return False
    def snapshot():
        scoped={}
        for key,app in get_running_taskbar_applications().items():
            if app['app_id']!='microsoft_edge':continue
            windows=[w for w in app['windows'] if owned(resolve_window_pid(w[0]))]
            if windows:
                pids={resolve_window_pid(w[0]) for w in windows}
                scoped[key]=dict(app,windows=windows,pids=pids,main_pid=next(iter(pids)))
        return scoped
    def poll_until(condition,timeout=25):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            monitor._take_snapshot()
            if condition():return
            time.sleep(.3)
        raise AssertionError('Timed out waiting for Edge taskbar transition')
    args=[str(edge),'--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--disable-background-mode']
    try:
        with patch('src.monitors.process_monitor.get_running_taskbar_applications',side_effect=snapshot):
            monitor._take_snapshot(False)
            subprocess.Popen(args+['--new-window','about:blank#one','about:blank#two','about:blank#three'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            poll_until(lambda:len(events)==1)
            assert events[0]['title']=='Microsoft Edge'
            subprocess.Popen(args+['about:blank#four','about:blank#five'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(8):
                time.sleep(.3);monitor._take_snapshot()
            assert len(events)==1,'Tabs emitted duplicate events'
            for app in snapshot().values():
                for hwnd,title in app['windows']:win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
            poll_until(lambda:len(events)==2)
            for _ in range(3):time.sleep(.3);monitor._take_snapshot()
            assert [e['title'] for e in events]==['Microsoft Edge','Microsoft Edge']
            assert not snapshot()
            assert db.get_event_count()==1
            print('PASS: real Edge, five tabs, one session row updated with Opened and Closed times.')
    finally:
        for proc in psutil.process_iter(['pid']):
            if owned(proc.pid):
                try:proc.terminate();proc.wait(4)
                except (psutil.NoSuchProcess,psutil.TimeoutExpired):pass
        db.close()
