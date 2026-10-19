"""Scale the live application layout to the available desktop work area."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QFrame


class WindowFitCanvas(QGraphicsView):
    """Keep the reference proportions without clipping at laptop resolutions.

    The scene contains the existing interactive widgets, including their live
    data, signals and keyboard handling. Qt maps pointer events through the
    same transform used to paint them.
    """
    DESIGN_WIDTH = 1672
    DESIGN_HEIGHT = 900

    def __init__(self, content, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setStyleSheet("QGraphicsView{border:none;background:#0b131c;padding:0}")
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                            QPainter.SmoothPixmapTransform)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        content.setFixedSize(self.DESIGN_WIDTH, self.DESIGN_HEIGHT)
        self.content = content
        self.proxy = scene.addWidget(content)
        self.setSceneRect(QRectF(0, 0, self.DESIGN_WIDTH, self.DESIGN_HEIGHT))
        self._fit_window()

    def _fit_window(self):
        self.setTransform(QTransform.fromScale(
            max(1, self.viewport().width()) / self.DESIGN_WIDTH,
            max(1, self.viewport().height()) / self.DESIGN_HEIGHT,
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_window()
