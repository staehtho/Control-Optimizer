import sys

from PySide6.QtWidgets import QApplication, QTextEdit, QWidget, QVBoxLayout, QGraphicsOpacityEffect, QLabel

if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = QWidget()
    layout = QVBoxLayout()
    txt = QTextEdit("123")
    txt.setEnabled(False)

    inactive_effect = QGraphicsOpacityEffect(txt)
    inactive_effect.setOpacity(0.45)
    txt.setGraphicsEffect(inactive_effect)

    layout.addWidget(txt)

    label = QLabel("Hello World")
    layout.addWidget(label)
    widget.setLayout(layout)

    widget.show()

    sys.exit(app.exec())
