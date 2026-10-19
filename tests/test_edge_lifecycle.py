"""Focused collector-to-database transition tests; never touch user history."""
import sys,tempfile,json
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.database import DatabaseManager
from src.monitors.process_monitor import ProcessMonitor
from src.monitors.monitor_manager import MonitorManager
from src.utils.app_metadata import resolve_application_info

def test_grouped_transitions():
    with tempfile.TemporaryDirectory() as folder:
        db=DatabaseManager(str(Path(folder)/'events.db'))
        manager=MonitorManager()
        for exe,name in [('msedge.exe','Microsoft Edge'),('code.exe','Visual Studio Code')]:
            info=resolve_application_info(exe,'C:/Apps/'+exe,[],2)
            key='C:/Apps/'+exe+'|group'
            app=dict(app_id=info.app_id,display_name=info.display_name,category=info.category,main_pid=100,
                     exe_path=info.exe_path,pids={100},windows=[(1000,'Tab 1')],app_info=info,aumid='group',username='test')
            monitor=ProcessMonitor()
            captured=[]
            monitor.event_detected.connect(captured.append)
            monitor.event_detected.connect(manager._on_event)
            state={}
            workers=[Mock(info=dict(pid=p,name=exe,exe=info.exe_path,cmdline=[exe,'--type='+role],ppid=100,memory_info=None))
                     for p,role in enumerate(['renderer','gpu-process','utility','background'],101)]
            with patch('src.monitors.process_monitor.get_running_taskbar_applications',side_effect=lambda:state),patch('src.monitors.process_monitor.psutil.process_iter',return_value=workers):
                monitor._take_snapshot(False)
                state[key]=app
                monitor._take_snapshot()
                monitor._take_snapshot()
                app['windows'].append((1001,'Tab 2'))
                app['main_pid']=200 # PID/window changes do not define a new logical app.
                monitor._take_snapshot()
                app['windows'].pop(0)
                monitor._take_snapshot()
                assert len(captured)==1
                opened=db.get_event_by_id(captured[0]['id'])
                state.clear() # Background processes still exist; last taskbar window is gone.
                monitor._take_snapshot()
                monitor._take_snapshot()
                assert [e['title'] for e in captured]==[name,name]
                assert captured[0]['id']==captured[1]['id']
                assert db.get_event_by_id(captured[0]['id'])['title']==opened['title']
                assert 'Closed:' in db.get_event_by_id(captured[0]['id'])['description']
                assert captured[1]['is_update']
                assert db.get_app_session(captured[1]['metadata']['session_db_id'])['status']=='closed'
                state[key]=app
                monitor._take_snapshot()
                state.clear()
                monitor._take_snapshot()
                assert len(captured)==4
            print('PASS:',name,'grouped Opened/Closed, PID/tab churn, lingering subprocesses, reopen and one updated session row')
        assert db.get_event_count()==4 # Manager did not insert duplicate pre-persisted events.
        db.close()

if __name__=='__main__':test_grouped_transitions()
