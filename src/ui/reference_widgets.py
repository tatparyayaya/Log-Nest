"""Reference artwork and reusable dashboard surfaces."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QPixmap, QPainterPath, QColor, QIcon
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton

ROOT = Path(__file__).resolve().parents[2]
SURFACE = 'QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #111e2b,stop:1 #0e1823);border:1px solid #243448;border-radius:34px}'

def surface():
    frame=QFrame()
    frame.setStyleSheet(SURFACE)
    return frame

def heading(text, size=24):
    label=QLabel(text)
    label.setStyleSheet(f"font-family:Cambria;font-size:{size}px;font-weight:600;color:#f5f6fb;background:transparent;border:none")
    return label

class ForestHeader(QFrame):
    def __init__(self):
        super().__init__()
        self.art=QPixmap(str(ROOT/'assets/forest-header.png'))
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path=QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),34,34)
        p.setClipPath(path)
        scaled = self.art.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
        p.drawPixmap(0, int((self.height()-scaled.height())*0.32), scaled)
        p.fillPath(path,QColor(6,15,25,115))
        p.setClipping(False)
        p.setPen(QColor('#28394e'))
        p.drawPath(path)
        p.end()

def symbol(label, kind, color, size=26):
    # Segoe's native monochrome icon font avoids platform-dependent emoji.
    glyphs={'monitor':'\ue7f4','grid':'\ue80a','layers':'\ue81e','warning':'\ue7ba','home':'\ue80f','clock':'\ue823','search':'\ue721','settings':'\ue713'}
    label.setText(glyphs.get(kind,kind))
    label.setStyleSheet(f"font-family:'Segoe MDL2 Assets';font-size:{size}px;color:{color};background:transparent;border:none")

class MetricCard(QFrame):
    def __init__(self,icon,title,color):
        super().__init__()
        self.setStyleSheet(SURFACE)
        self.setFixedHeight(112)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(22,17,22,15)
        row=QHBoxLayout()
        badge=QLabel()
        symbol(badge,icon,color,24)
        row.addWidget(badge)
        text=QLabel(title.upper())
        text.setStyleSheet('font-size:14px;color:#91aaca;background:transparent;border:none')
        row.addWidget(text,1)
        trailing=QLabel('›' if icon=='warning' else '↗' if icon=='grid' else '\ue916' if icon=='monitor' else '\ue80a')
        trailing.setStyleSheet(f'font-family:Segoe MDL2 Assets;font-size:23px;color:{color};background:transparent;border:none')
        row.addWidget(trailing)
        layout.addLayout(row)
        self.value_label=heading('0',32)
        layout.addWidget(self.value_label)
    def set_value(self,value):
        self.value_label.setText(str(value))

def disclosure(layout,title,content,extra=None):
    row=QHBoxLayout()
    button=QPushButton(title)
    button.setStyleSheet("QPushButton{font-family:Cambria;font-size:23px;color:#f5f6fb;text-align:left;border:none;background:transparent;padding:10px 0}")
    button.setCursor(Qt.PointingHandCursor)
    button.setCheckable(True)
    row.addWidget(button,1)
    if extra is not None: row.addWidget(extra)
    arrow=QLabel('›')
    arrow.setStyleSheet('font-size:30px;color:#91aaca;border:none;background:transparent')
    row.addWidget(arrow)
    layout.addLayout(row)
    layout.addWidget(content)
    content.hide()
    button.toggled.connect(content.setVisible)
    button.toggled.connect(lambda checked: arrow.setText('⌄' if checked else '›'))
    return button
