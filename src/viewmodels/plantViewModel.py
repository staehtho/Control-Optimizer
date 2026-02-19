from PySide6.QtCore import QObject, Signal, Property

from .baseViewModel import BaseViewModel
from models import PlantModel
from services.controlsys import Plant

class PlantViewModel(BaseViewModel):

    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()

    def __init__(self, plant_modle: PlantModel, parent: QObject = None):

        super().__init__(parent)

        self._plant_model = plant_modle

        self._connect_signals()


    def _connect_signals(self):
        # PlantModel
        self._plant_model.numChanged.connect(self._on_model_num_changed)
        self._plant_model.denChanged.connect(self._on_model_den_changed)
        self._plant_model.isValidChanged.connect(self._on_model_is_valid_changed)

    # -------------------
    # num
    # -------------------
    def _on_model_num_changed(self):
        if not self.check_update_allowed("plant_num"):
            self._logger.debug("Blocked 'num' update (guard active)")
            return

        new_value = self._plant_model.num
        self._logger.debug(f": Forwarding 'num' change from model (new_value={new_value})")
        self.numChanged.emit()

    def _get_num(self) -> list[float]:
        return self._plant_model.num

    def _set_num(self, value: list[float]) -> None:
        if self._plant_model.num == value:
            return

        with self.updating("plant_num"):
            self._plant_model.num = value
            self.numChanged.emit()

    num = Property(list, _get_num, _set_num, notify=numChanged)  # type: ignore[assignment]

    # -------------------
    # den
    # -------------------
    def _on_model_den_changed(self):
        if not self.check_update_allowed("plant_den"):
            self._logger.debug("Blocked 'den' update (guard active)")
            return

        new_value = self._plant_model.den
        self._logger.debug(f"Forwarding 'den' change from model (new_value={new_value})")
        self.denChanged.emit()

    def _get_den(self) -> list[float]:
        return self._plant_model.den

    def _set_den(self, value: list[float]) -> None:
        if self._plant_model.den == value:
            return

        with self.updating("plant_den"):
            self._plant_model.den = value
            self.denChanged.emit()

    den = Property(list, _get_den, _set_den, notify=denChanged)  # type: ignore[assignment]

    # -------------------
    # plant Property (read-only)
    # -------------------
    def get_plant(self) -> Plant:
        return self._plant_model.get_plant()

    # -------------------
    # is_valid
    # -------------------
    def _on_model_is_valid_changed(self):
        if not self.check_update_allowed("plant_is_valid"):
            self._logger.debug("Blocked 'is_valid' update (guard active)")
            return

        new_value = self._plant_model.is_valid
        self._logger.debug(f"Forwarding 'is_valid' change from model (new_value={new_value})")
        self.isValidChanged.emit()

    def _get_is_valid(self) -> list[float]:
        return self._plant_model.den

    is_valid = Property(list, _get_is_valid, notify=isValidChanged)  # type: ignore[assignment]