"""Swipeable live window cards; all durations are elapsed wall-clock time."""
import ctypes
from ctypes import wintypes
import time
from PySide6.QtCore import Qt, Signal, QTimer, QFileInfo, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame,QWidget,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QScrollArea,QFileIconProvider,QSizePolicy
from src.ui.reference_widgets import SURFACE, heading


def window_icon(window):
    """Copy the window's real icon without taking ownership of its native HICON."""
    user=ctypes.windll.user32
    user.SendMessageTimeoutW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM,wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
    user.GetClassLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int]
    user.GetClassLongPtrW.restype=ctypes.c_size_t
    result=ctypes.c_size_t()
    hwnd=window['hwnd']
    for size in (1,0,2):
        user.SendMessageTimeoutW(hwnd,0x007f,size,0,0x0002,40,ctypes.byref(result))
        if result.value:
            image=QImage.fromHICON(result.value)
            if not image.isNull(): return QPixmap.fromImage(image)
    handle=user.GetClassLongPtrW(hwnd,-14) or user.GetClassLongPtrW(hwnd,-34)
    if handle:
        image=QImage.fromHICON(handle)
        if not image.isNull(): return QPixmap.fromImage(image)
    provider=QFileIconProvider()
    icon=provider.icon(QFileInfo(window['exe_path'])) if window.get('exe_path') else provider.icon(QFileIconProvider.File)
    return icon.pixmap(56,56)


class OpenWindowCard(QFrame):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window=window
        self.setStyleSheet('QFrame{background:#142131;border:1px solid #293b51;border-radius:24px}')
        layout=QVBoxLayout(self)
        layout.setContentsMargins(22,22,22,22)
        layout.setSpacing(14)
        top=QHBoxLayout()
        self.icon_label=QLabel()
        self.icon_label.setFixedSize(58,58)
        self.icon_label.setStyleSheet('border:none;background:transparent')
        self.icon_label.setPixmap(window_icon(window).scaled(54,54,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        top.addWidget(self.icon_label)
        self.name=heading(window['app_name'],22)
        self.name.setWordWrap(True)
        self.name.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        top.addWidget(self.name,1)
        layout.addLayout(top)
        self.title=QLabel(window['title'])
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(48)
        self.title.setStyleSheet('font-size:14px;color:#91aaca;border:none;background:transparent')
        layout.addWidget(self.title)
        layout.addStretch()
        self.elapsed=heading('00:00:00',36)
        self.elapsed.setStyleSheet('font-family:Cambria;font-size:36px;color:#00bfff;border:none;background:transparent')
        layout.addWidget(self.elapsed)
        self.caption=QLabel('Observed open for' if window['preexisting'] else 'Open for')
        self.caption.setStyleSheet('font-size:14px;color:#91aaca;border:none;background:transparent')
        layout.addWidget(self.caption)
        self.setToolTip('This window was already open when tracking started; the timer begins at first observation.' if window['preexisting'] else 'Elapsed time since this taskbar window was first detected (updated every second).')
        self.update_window(window)

    def update_window(self, window):
        self.window=window
        self.title.setText(window['title'])
        self.tick()

    def tick(self):
        seconds=max(0,int(time.monotonic()-self.window['observed_at']))
        self.elapsed.setText(f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}')


class ActiveWindowsCarousel(QFrame):
    set_limit_requested=Signal(str,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(SURFACE)
        self._cards={}
        self._order=[]
        self._index=0
        self._press=None
        layout=QVBoxLayout(self)
        layout.setContentsMargins(26,24,26,24)
        layout.setSpacing(18)
        header=QHBoxLayout()
        header.addWidget(heading('Active Windows',24),1)
        self.prev=QPushButton('‹')
        self.next=QPushButton('›')
        for button in (self.prev,self.next):
            button.setFixedSize(38,38)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet('QPushButton{background:#1a293b;border:1px solid #2a3c53;border-radius:13px;color:#d7e6fa;font-size:26px} QPushButton:disabled{color:#52647a} QPushButton:hover{border-color:#0863f6}')
            header.addWidget(button)
        self.prev.setAccessibleName('Previous open window')
        self.next.setAccessibleName('Next open window')
        self.prev.clicked.connect(lambda:self.navigate(-1))
        self.next.clicked.connect(lambda:self.navigate(1))
        layout.addLayout(header)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet('QScrollArea{border:none;background:transparent} QScrollArea>QWidget>QWidget{background:transparent}')
        self.track=QWidget()
        self.row=QHBoxLayout(self.track)
        self.row.setContentsMargins(0,0,0,0)
        self.row.setSpacing(14)
        self.scroll.setWidget(self.track)
        self.scroll.viewport().installEventFilter(self)
        layout.addWidget(self.scroll,1)
        self.empty=QLabel('No open taskbar windows')
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet('font-size:16px;color:#91aaca;border:none;background:transparent')
        self.row.addWidget(self.empty)
        footer=QHBoxLayout()
        self.position=QLabel('0 windows')
        self.position.setStyleSheet('color:#91aaca;font-size:14px;border:none;background:transparent')
        footer.addWidget(self.position,1)
        self.limit=QPushButton('Set Limit')
        self.limit.setStyleSheet('background:#1a293b;color:#b9cce5;border:1px solid #293b51;border-radius:12px;padding:8px 14px;font-size:14px')
        self.limit.clicked.connect(self._limit)
        footer.addWidget(self.limit)
        layout.addLayout(footer)
        self.animation=QPropertyAnimation(self.scroll.horizontalScrollBar(),b'value',self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self._timer=QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._controls()

    def set_windows(self, windows):
        selected=self._order[self._index] if self._order else None
        incoming={tuple(w['key']):w for w in windows}
        for key in list(self._cards):
            if key not in incoming:
                card=self._cards.pop(key)
                self.row.removeWidget(card)
                card.hide()
                card.deleteLater()
        for key,window in incoming.items():
            if key not in self._cards:
                card=OpenWindowCard(window)
                card.installEventFilter(self)
                for label in card.findChildren(QLabel): label.installEventFilter(self)
                self._cards[key]=card
                self.row.addWidget(card)
            else: self._cards[key].update_window(window)
        self._order=list(self._cards)
        self._index=self._order.index(selected) if selected in self._order else min(self._index,max(0,len(self._order)-1))
        self.empty.setVisible(not self._order)
        self._resize_cards()
        self._controls()
        QTimer.singleShot(0,self._snap)

    def _resize_cards(self):
        width=max(1,self.scroll.viewport().width())
        for card in self._cards.values(): card.setFixedWidth(width)
        count=len(self._cards)
        self.track.setFixedWidth(max(width,count*width+max(0,count-1)*self.row.spacing()))
        self.row.activate()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._resize_cards()
        QTimer.singleShot(0,self._snap)

    def _snap(self):
        if self._order:
            self.scroll.horizontalScrollBar().setValue(self._index*(self.scroll.viewport().width()+self.row.spacing()))

    def navigate(self,step):
        self._index=max(0,min(len(self._order)-1,self._index+step))
        self._controls()
        self.animation.stop()
        self.animation.setStartValue(self.scroll.horizontalScrollBar().value())
        self.animation.setEndValue(self._index*(self.scroll.viewport().width()+self.row.spacing()))
        self.animation.start()

    def _controls(self):
        count=len(self._order)
        self.prev.setEnabled(self._index>0)
        self.next.setEnabled(self._index+1<count)
        self.limit.setVisible(bool(count))
        self.position.setText(f"{self._index+1} of {count} {'window' if count == 1 else 'windows'}" if count else '0 windows')

    def _tick(self):
        for card in self._cards.values(): card.tick()

    def _limit(self):
        if self._order:
            window=self._cards[self._order[self._index]].window
            self.set_limit_requested.emit(window['app_id'],window['app_name'])

    def eventFilter(self,watched,event):
        if watched is self.scroll.viewport() and event.type()==QEvent.Resize:
            self._resize_cards()
            QTimer.singleShot(0,self._snap)
        if event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:
            self._press=event.globalPosition()
        elif event.type()==QEvent.MouseMove and self._press is not None:
            return True
        elif event.type()==QEvent.MouseButtonRelease and self._press is not None:
            delta=event.globalPosition().x()-self._press.x()
            self._press=None
            if abs(delta)>35:
                self.navigate(-1 if delta>0 else 1)
                return True
        elif event.type()==QEvent.Wheel:
            delta=event.pixelDelta().x() or event.angleDelta().x() or event.angleDelta().y()
            if delta:
                self.navigate(1 if delta<0 else -1)
                return True
        return super().eventFilter(watched,event)
