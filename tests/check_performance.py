"""Verify reduced refresh work without changing visible data or collectors."""
import os,sys,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from datetime import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtTest import QTest
from src.database import DatabaseManager
from src.ui.main_window import MainWindow
from src.ui.widgets import TimelineEventCard,_application_icon,ui_is_presented
app=QApplication([])
for f in ['segoeui.ttf','cambria.ttc']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)
folder=tempfile.TemporaryDirectory()
db=DatabaseManager(str(Path(folder.name)/'performance.db'))
for i in range(10):db.insert_event('app_session','Application','Notepad',source='Notepad',metadata={'executable':'C:/Windows/System32/notepad.exe'})
w=MainWindow();w._start_monitors_timer.stop();w._dashboard._refresh_timer.stop();w._timeline._refresh_timer.stop()
w.show();app.processEvents()
w._switch_page(1);w._timeline.load_events();app.processEvents()
page=w._timeline
cards=page.events_widget.findChildren(TimelineEventCard)
assert len(cards)==10
with patch.object(page.db,'get_events',wraps=page.db.get_events) as read:
    page._load_page();app.processEvents()
    assert page.events_widget.findChildren(TimelineEventCard)==cards
    assert read.call_count==1
assert _application_icon.cache_info().misses==1
assert _application_icon.cache_info().hits>=9
# A changed DB row must still repaint, even though event count stays unchanged.
db.update_event(cards[0].event_data['id'],description='Changed description')
page._load_page();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.processEvents()
assert any(c.event_data['description']=='Changed description' for c in page.events_widget.findChildren(TimelineEventCard))
assert page.events_widget.findChildren(TimelineEventCard)!=cards
# Hidden/tray UI should not query/redraw; visible UI still coalesces event bursts.
w.hide();app.processEvents()
with patch.object(w._dashboard,'refresh_data') as refresh:
    w._dashboard._refresh_visible()
    assert not refresh.called
w.show();w._switch_page(0);app.processEvents()
assert ui_is_presented(w._dashboard)
w._dashboard._event_refresh_timer.stop()
with patch.object(w._dashboard,'refresh_data') as refresh:
    for _ in range(100):w._dashboard.add_live_event({})
    QTest.qWait(250)
    assert refresh.call_count==1,refresh.call_count
w._tray.hide();w.hide();db.close()
print('PASS: unchanged rows reused; DB edits refresh; native icons cached; hidden UI skips redraw; 100 events coalesce to one refresh')
