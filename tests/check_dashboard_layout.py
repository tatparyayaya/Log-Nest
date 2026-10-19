import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os, tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['USERPROFILE']=tempfile.mkdtemp(prefix='lognest-ui-check-')
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QCoreApplication,QEvent
from src.ui.main_window import MainWindow
app=QApplication([])
for f in ['segoeui.ttf','cambria.ttc','georgia.ttf','georgiab.ttf','segmdl2.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)
w=MainWindow(); w._start_monitors_timer.stop(); w.resize(1672,900); w.show()
p=w._dashboard.wellbeing_page
from unittest.mock import patch
from PySide6.QtGui import QPixmap
from src.monitors.taskbar_window_monitor import WindowLifetimes
import time
with patch('src.ui.active_windows.window_icon',return_value=QPixmap(54,54)):
    p.live_card.set_windows(WindowLifetimes().reconcile([
        dict(hwnd=1,pid=100,process_started=1,app_id='editor',app_name='Visual Studio Code',exe_path='',title='A long document name — Visual Studio Code'),
        dict(hwnd=2,pid=101,process_started=1,app_id='browser',app_name='Google Chrome',exe_path='',title='Second open window'),
    ],time.monotonic()-125))
for name, seconds in [("VS Code",2880),("Google Chrome",960),("Lognest",780),("Antigravity IDE",180)]:
    p.db.record_screen_time(name.lower().replace(' ',''), name, "Application", seconds, date_str=p._current_date,hour=18)
p.refresh_data(); app.processEvents(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete); app.processEvents()
assert p.stat_limits.isVisible()
assert p.live_card.geometry().right() < p.width()
original=p._current_date
p._prev_day(); assert p._current_date!=original
p._go_today(); assert p._current_date==original
for name in ['Application Usage','Hourly Activity (Today)']:
    btn=next(b for b in p.findChildren(QPushButton) if b.text()==name)
    btn.click(); app.processEvents(); assert btn.isChecked()
    btn.click(); app.processEvents(); assert not btn.isChecked()
for i in range(4): w._switch_page(i); assert w._page_stack.currentIndex()==i
w._switch_page(0)
w._dashboard._switch_view(1); assert w._dashboard.stack.currentIndex()==1
w._dashboard._switch_view(0)
p.on_active_tick({'app_id':'lognest','app_name':'Lognest','category':'Application','session_seconds':124,'app_today_seconds':794,'today_total_seconds':5160})
app.processEvents(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete); app.processEvents()
assert not w.grab().isNull()
assert p.live_card.position.text() == "1 of 2 windows"
# Exercise the user's 1366x768 desktop after title bar/taskbar space,
# other common laptop work areas, and the full reference size.
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
for width, height in [(1366,705), (1280,680), (1024,576), (1536,824), (1672,900)]:
    w.resize(width,height)
    app.processEvents()
    canvas=w._fit_canvas
    bounds=canvas.mapFromScene(canvas.sceneRect()).boundingRect()
    assert abs(bounds.width()-canvas.viewport().width()) <= 2
    assert abs(bounds.height()-canvas.viewport().height()) <= 2
    assert p.live_card.geometry().right() < p.width()
    for card in p.live_card._cards.values():
        assert card.height() <= p.live_card.scroll.viewport().height(), (card.height(),p.live_card.scroll.viewport().height())
    content_scroll=next(a for a in p.findChildren(__import__('PySide6.QtWidgets',fromlist=['QScrollArea']).QScrollArea) if a.widget() is not p.apps_container_widget)
    assert content_scroll.verticalScrollBar().maximum()==0, (width,height,'dashboard overflows vertically')
    assert content_scroll.widget().width() <= content_scroll.viewport().width(), (width,height,'dashboard overflows horizontally')
    assert content_scroll.widget().rect().contains(p.stat_limits.mapTo(content_scroll.widget(),p.stat_limits.rect().bottomRight()))
    next_button=p.live_card.next
    next_point=next_button.mapTo(canvas.content,next_button.rect().center())
    QTest.mouseClick(canvas.viewport(),Qt.LeftButton,pos=canvas.mapFromScene(next_point))
    app.processEvents()
    assert p.live_card._index==1
    p.live_card.navigate(-1)
    app.processEvents()
    # Click through the scaled surface to verify event coordinates and tabs.
    button=w._dashboard.btn_tab_activity
    point=button.mapTo(canvas.content,button.rect().center())
    QTest.mouseClick(canvas.viewport(),Qt.LeftButton,pos=canvas.mapFromScene(point))
    app.processEvents()
    assert w._dashboard.stack.currentIndex()==1
    w._dashboard._switch_view(0)
    app.processEvents()
w.resize(1366,705)
app.processEvents()
assert not w.grab().isNull()
w._tray.hide()
print('PASS: rendering, live updates, date navigation, disclosures, pages, and dashboard tabs')
