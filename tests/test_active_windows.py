"""Taskbar eligibility, independent lifetimes, and carousel interaction checks."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import time
import unittest
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap,QFontDatabase
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from src.monitors.taskbar_window_monitor import WindowLifetimes,TaskbarWindowMonitor
from src.utils.app_metadata import is_taskbar_window
from src.ui.active_windows import ActiveWindowsCarousel


def record(hwnd,title='Document',pid=10):
    return dict(hwnd=hwnd,pid=pid,process_started=100,app_id='editor',app_name='Editor',title=title,exe_path='')


class LifetimesTest(unittest.TestCase):
    def test_independent_windows_close_reopen_and_handle_reuse(self):
        model=WindowLifetimes()
        first=model.reconcile([record(1)],now=10)
        self.assertTrue(first[0]['preexisting'])
        two=model.reconcile([record(2),record(1,'Renamed')],now=20)
        self.assertEqual([r['hwnd'] for r in two],[1,2])
        self.assertEqual(two[0]['observed_at'],10)
        self.assertEqual(two[1]['observed_at'],20)
        self.assertFalse(two[1]['preexisting'])
        self.assertEqual(two[0]['title'],'Renamed')
        model.reconcile([record(2)],now=30)
        reopened=model.reconcile([record(1),record(2)],now=40)
        self.assertEqual(reopened[1]['observed_at'],40)
        reused=model.reconcile([record(1,pid=12)],now=50)
        self.assertEqual(reused[0]['observed_at'],50)
        self.assertEqual(model.reconcile([],now=60),[])

    def test_taskbar_rules(self):
        user=Mock()
        user.IsWindowVisible.return_value=True
        user.GetWindowLongW.return_value=0
        user.GetWindow.return_value=0
        user.GetWindowTextLengthW.return_value=8
        user.IsIconic.return_value=False
        def rect(hwnd,ptr):
            ptr._obj.right=800;ptr._obj.bottom=600
            return 1
        def title(hwnd,buffer,count):buffer.value='Document';return 8
        user.GetWindowRect.side_effect=rect
        user.GetWindowTextW.side_effect=title
        dwm=Mock()
        dwm.DwmGetWindowAttribute.return_value=0
        with patch('ctypes.windll.user32',user),patch('ctypes.windll.dwmapi',dwm):
            self.assertTrue(is_taskbar_window(1)[0])
            user.GetWindow.return_value=None  # HWND NULL with pointer-safe ctypes signatures
            self.assertTrue(is_taskbar_window(1)[0])
            user.GetWindow.return_value=0
            user.IsWindowVisible.return_value=False
            self.assertFalse(is_taskbar_window(1)[0])
            user.IsWindowVisible.return_value=True
            user.GetWindowLongW.return_value=0x80
            self.assertFalse(is_taskbar_window(1)[0])
            user.GetWindowLongW.return_value=0
            user.GetWindow.return_value=2
            self.assertFalse(is_taskbar_window(1)[0])
            user.GetWindowLongW.return_value=0x40000
            self.assertTrue(is_taskbar_window(1)[0])
            user.GetWindow.return_value=0
            user.GetWindowLongW.return_value=0
            def cloak(hwnd,attr,ptr,size):ptr._obj.value=1;return 0
            dwm.DwmGetWindowAttribute.side_effect=cloak
            self.assertFalse(is_taskbar_window(1)[0])
            dwm.DwmGetWindowAttribute.side_effect=None
            def zero_rect(hwnd,ptr):return 1
            user.GetWindowRect.side_effect=zero_rect
            self.assertFalse(is_taskbar_window(1)[0])
            user.IsIconic.return_value=True
            self.assertTrue(is_taskbar_window(1)[0])


class CarouselTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        for f in ['segoeui.ttf','cambria.ttc']:
            QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)

    def test_navigation_swipe_live_time_limits_and_removal(self):
        with patch('src.ui.active_windows.window_icon',return_value=QPixmap(54,54)):
            widget=ActiveWindowsCarousel()
            widget.resize(510,396)
            widget.show()
            model=WindowLifetimes()
            windows=model.reconcile([record(1),record(2,'Second document'),record(3,'Third')],time.monotonic()-65)
            widget.set_windows(windows)
            self.app.processEvents()
            self.assertEqual(len(widget._cards),3)
            cards=list(widget._cards.values())
            viewport_width=widget.scroll.viewport().width()
            self.assertTrue(all(c.width()==viewport_width for c in cards))
            self.assertGreaterEqual(cards[1].x(),cards[0].x()+cards[0].width())
            self.assertGreaterEqual(cards[2].x(),cards[1].x()+cards[1].width())
            self.assertFalse(widget.prev.isEnabled())
            card=widget._cards[windows[0]['key']]
            self.assertEqual(card.elapsed.text(),'00:01:05')
            with patch('src.ui.active_windows.time.monotonic',return_value=windows[0]['observed_at']+67):widget._tick()
            self.assertEqual(card.elapsed.text(),'00:01:07')
            QTest.mouseClick(widget.next,Qt.LeftButton)
            QTest.qWait(220)
            self.assertEqual(widget._index,1)
            viewport=widget.scroll.viewport()
            QTest.mousePress(viewport,Qt.LeftButton,pos=QPoint(280,60))
            QTest.mouseMove(viewport,QPoint(90,60))
            QTest.mouseRelease(viewport,Qt.LeftButton,pos=QPoint(90,60))
            QTest.qWait(220)
            self.assertEqual(widget._index,2)
            self.assertFalse(widget.next.isEnabled())
            emitted=[]
            widget.set_limit_requested.connect(lambda *args:emitted.append(args))
            widget.limit.click()
            self.assertEqual(emitted,[('editor','Editor')])
            widget.set_windows([windows[0]])
            self.app.processEvents()
            self.assertEqual(widget._index,0)
            self.assertEqual(len(widget._cards),1)
            widget.set_windows([])
            self.app.processEvents()
            self.assertTrue(widget.empty.isVisible())
            self.assertFalse(widget.limit.isVisible())
            widget.close()
            widget.deleteLater()

    def test_worker_snapshot_and_clean_stop(self):
        received=[]
        monitor=TaskbarWindowMonitor()
        monitor.windows_changed.connect(received.append)
        with patch('src.monitors.taskbar_window_monitor.enumerate_taskbar_windows',return_value=[record(4)]):
            monitor.start()
            for _ in range(15):
                QTest.qWait(20)
                if received:break
            monitor.stop()
        self.assertFalse(monitor.isRunning())
        self.assertTrue(received)
        self.assertEqual(received[0][0]['hwnd'],4)


if __name__=='__main__':unittest.main()
