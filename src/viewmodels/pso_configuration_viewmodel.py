from PySide6.QtCore import QObject, Signal, Property, Slot

from models import ModelContainer, PlantModel, PsoConfigurationModel, SettingsModel
from .base_viewmodel import BaseViewModel


class PsoConfigurationViewModel(BaseViewModel):

    plantChanged = Signal()
    starTimeChanged = Signal()
    endTimeChanged = Signal()

    def __init__(self, model_container: ModelContainer, parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._model_function = model_container.model_function
        self._model_pso: PsoConfigurationModel = model_container.model_pso
        self._settings: SettingsModel = model_container.model_settings

        self._connect_signals()

    def _connect_signals(self) -> None:
        # PlantModel
        self._model_plant.modelChanged.connect(self.plantChanged.emit)

    # -------------------
    # plant
    # -------------------
    @Slot()
    def get_plant_num_den(self) -> tuple[list[float], list[float]]:
        self._logger.debug(f"'get_plant_num_den' called (value=({self._model_plant.num}, {self._model_plant.den}))")
        return self._model_plant.num, self._model_plant.den

    # -------------------
    # start time
    # -------------------
    def _get_start_time(self) -> float:
        value = self._model_pso.start_time
        self._logger.debug(f"Getter 'start_time' called (value={value})")
        return value

    def _set_start_time(self, value: float) -> None:
        self._logger.debug(f"Setter 'start_time' called (value={value})")

        if self._model_pso.start_time == value:
            self._logger.debug("Skipped 'start_time' update (same value)")
            return

        if self._model_pso.end_time <= value:
            self._logger.debug(f"Skipped 'start_time' update (value={value} >= end_time={self._model_pso.end_time})")
            return

        with self.updating("pso_start_time"):
            self._model_pso.start_time = value
            self._logger.debug("Emitting starTimeChanged after model update")
            self._logger.debug(f"PsoFunctionModel 'start_time' updated (value={value})")
            self.starTimeChanged.emit()

    start_time = Property(float, _get_start_time, _set_start_time, notify=starTimeChanged)  # type: ignore[assignment]

    # -------------------
    # end time
    # -------------------
    def _get_end_time(self) -> float:
        value = self._model_pso.end_time
        self._logger.debug(f"Getter 'end_time' called (value={value})")
        return value

    def _set_end_time(self, value: float) -> None:
        self._logger.debug(f"Setter 'end_time' called (value={value})")

        if self._model_pso.end_time == value:
            self._logger.debug("Skipped 'end_time' update (same value)")
            return

        if self._model_pso.start_time >= value:
            self._logger.debug(f"Skipped 'end_time' update (value={value} <= start_time={self._model_pso.start_time})")
            return

        with self.updating("pso_end_time"):
            self._model_pso.end_time = value
            self._logger.debug("Emitting endTimeChanged after model update")
            self._logger.debug(f"PsoFunctionModel 'end_time' updated (value={value})")
            self.endTimeChanged.emit()

    end_time = Property(float, _get_end_time, _set_end_time, notify=endTimeChanged)  # type: ignore[assignment]