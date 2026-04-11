from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette


class BaseBanner(QWidget):
    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(parent)

        self.setObjectName("Banner")  # important for CSS targeting

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        self.label = QLabel(text)
        self.label.setObjectName("BannerLabel")
        layout.addWidget(self.label)

        self.setFixedHeight(40)
        self.setVisible(False)

        # fade animation
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def show_banner(self, duration_ms: int = 2500):
        self.setWindowOpacity(0.0)
        self.setVisible(True)

        # Create a fresh animation every time
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        QTimer.singleShot(duration_ms, self.hide_banner)

    def hide_banner(self):
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()
        self._anim.finished.connect(lambda: self.setVisible(False))
