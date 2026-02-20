from PySide6.QtCore import QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io

from viewmodels import LanguageViewModel, PlantViewModel
from .baseView import BaseView

class PlantView(BaseView, QWidget):
    def __init__(self, lang_vm: LanguageViewModel, plant_vm: PlantViewModel, parent: QObject = None):
        QWidget.__init__(self, parent)
        self._vm = plant_vm

        BaseView.__init__(self, lang_vm)


    def _init_ui(self) -> None:
        main_layout = QGridLayout()

        # num
        self._lbl_num = QLabel(self.tr("plant.num"))
        self._txt_num = QLineEdit()
        self._txt_num.setPlaceholderText("b_n, b_n-1, ..., b_1, b_0")

        main_layout.addWidget(self._lbl_num, 0, 0)
        main_layout.addWidget(self._txt_num, 0, 1)

        # den
        self._lbl_den = QLabel(self.tr("plant.den"))
        self._txt_den = QLineEdit()
        self._txt_den.setPlaceholderText("a_n, a_n-1, ..., a_1, a_0")

        main_layout.addWidget(self._lbl_den, 1, 0)
        main_layout.addWidget(self._txt_den, 1, 1)

        # plant
        self._lbl_plant = QLabel()
        self._lbl_plant.setPixmap(self.latex_to_pixmap(r"G(s) = \frac{b_n s^n}{b_n s^n}"))

        main_layout.addWidget(self._lbl_plant, 0, 2, 2, 2)

        self.setLayout(main_layout)


    def _connect_signals(self) -> None:
        self._txt_num.returnPressed.connect(self._on_txt_num_return_pressed)
        self._txt_den.returnPressed.connect(self._on_txt_den_return_pressed)

    def _bind_vm(self) -> None:
        self._vm.numChanged.connect(self._on_vm_num_changed)
        self._vm.denChanged.connect(self._on_vm_den_changed)

    def _retranslate(self) -> None:
        self._lbl_num.setText(self.tr("plant.num"))
        self._lbl_den.setText(self.tr("plant.den"))

    def _on_vm_num_changed(self) -> None:
        self._txt_num.setText(self._vm.num)

    def _on_vm_den_changed(self) -> None:
        self._txt_den.setText(self._vm.den)

    def _on_txt_num_return_pressed(self) -> None:
        self._vm.num = self._txt_num.text()

    def _on_txt_den_return_pressed(self) -> None:
        self._vm.den = self._txt_den.text()

    @staticmethod
    def latex_to_pixmap(text: str) -> QPixmap:
        fig = plt.figure()
        fig.text(0, 0, f"${text}$")
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        buf.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        return pixmap