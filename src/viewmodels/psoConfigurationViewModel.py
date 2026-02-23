from PySide6.QtCore import QObject, Signal, Property, Slot

from models import PsoConfigurationModel, SettingsModel
from .baseViewModel import BaseViewModel

class PsoConfigurationViewModel(BaseViewModel):

    starTimeChanged = Signal()
    endTimeChanged = Signal()

    def __init__(self, model_pso: PsoConfigurationModel, settings: SettingsModel, parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_pso = model_pso
        self._settings = settings

