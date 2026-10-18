"""
Generate Windows .ico file for LOG NEST
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

size = 256
pixmap = QPixmap(size, size)
pixmap.fill(QColor("transparent"))

painter = QPainter(pixmap)
painter.setRenderHint(QPainter.Antialiasing)

# Background rounded square with gradient look
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#141E2E"))
painter.drawRoundedRect(0, 0, size, size, 56, 56)

# Outer glow / border
painter.setPen(QPen(QColor("#6C63FF"), 8))
painter.setBrush(QColor("#1A2438"))
painter.drawRoundedRect(8, 8, size - 16, size - 16, 48, 48)

# Accent highlight
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#6C63FF"))
painter.drawRoundedRect(36, 36, size - 72, size - 72, 36, 36)

# Letter / Emblem
painter.setPen(QPen(QColor("#FFFFFF"), 0))
painter.setBrush(QColor("#FFFFFF"))
font = QFont("Segoe UI", 80, QFont.Bold)
painter.setFont(font)
painter.drawText(pixmap.rect(), Qt.AlignCenter, "LN")

painter.end()

pixmap.save("app_icon.ico", "ICO")
pixmap.save("app_icon.png", "PNG")
print("Saved app_icon.ico and app_icon.png")
