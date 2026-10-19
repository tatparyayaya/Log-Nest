import os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QScrollArea,QWidget,QVBoxLayout,QLabel
from PySide6.QtGui import QFontDatabase
from src.ui.widgets import TimelineEventCard
from src.ui.theme import get_main_stylesheet
app=QApplication([])
QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
scroll=QScrollArea();scroll.setStyleSheet(get_main_stylesheet());scroll.setWidgetResizable(True)
content=QWidget();layout=QVBoxLayout(content);layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
cards=[]
for i in range(5):
    card=TimelineEventCard(dict(title='Notepad',event_type='app_session',category='Application',metadata=dict(executable='C:/Windows/System32/notepad.exe',opened_at='2026-10-19T13:45:00',closed_at='2026-10-19T13:46:00',duration_formatted='1m'),severity='info'))
    cards.append(card);layout.addWidget(card)
layout.addStretch();scroll.setWidget(content);scroll.resize(900,660);scroll.show()
for _ in range(4):app.processEvents()
assert not cards[0].icon_label.pixmap().isNull()
assert cards[3].geometry().bottom()<scroll.viewport().height()
assert cards[4].geometry().top()>=scroll.viewport().height()
assert any('Opened: 01:45 PM  |  Closed: 01:46 PM' == l.text() for l in cards[0].findChildren(QLabel))
for height in [460,540,660,800]:
    scroll.resize(900,height)
    for _ in range(4):app.processEvents()
    assert cards[3].geometry().bottom()<scroll.viewport().height()
    assert cards[4].geometry().top()>=scroll.viewport().height()
    assert scroll.verticalScrollBar().maximum()>0
assert 'background:#1c2b44' in cards[0].styleSheet()
print('PASS: exactly four timeline rows fit at every tested height; remaining entries scroll; real icons and session details preserved')
scroll.close()
