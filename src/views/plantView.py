from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from viewmodels import LanguageViewModel, PlantViewModel
from .baseView import BaseView

class PlantView(BaseView, QWidget):
    def __init__(self, lang_vm: LanguageViewModel, plant_vm: PlantViewModel, parent: QObject = None):
        QWidget.__init__(self, parent)
        BaseView.__init__(self, lang_vm)

        self._plant_vm = plant_vm

    def _init_ui(self) -> None:
        pass

    def _connect_signals(self) -> None:
        pass

    def _bind_viewmodel(self) -> None:
        pass

    def _retranslate(self) -> None:
        pass