from PySide6.QtCore import QObject, Signal, Slot

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from models import ModelContainer, PlantModel, PsoConfigurationModel, SettingsModel
from .base_viewmodel import BaseViewModel


class PsoConfigurationViewModel(BaseViewModel):

    plantChanged = Signal()
    startTimeChanged = Signal()
    endTimeChanged = Signal()
    antiWindupChanged = Signal()
    excitationTargetChanged = Signal()
    performanceIndexChanged = Signal()
    constraintMinChanged = Signal()
    constraintMaxChanged = Signal()
    kpMinChanged = Signal()
    kpMaxChanged = Signal()
    tiMinChanged = Signal()
    tiMaxChanged = Signal()
    tdMinChanged = Signal()
    tdMaxChanged = Signal()

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
        self.logger.debug(f"'get_plant_num_den' called (value=({self._model_plant.num}, {self._model_plant.den}))")
        return self._model_plant.num, self._model_plant.den

    # -------------------
    # start time
    # -------------------
    def _verify_start_time(self, value: float) -> bool:
        if self._model_pso.end_time <= value:
            self.logger.debug(f"Skipped 'start_time' update (value={value} >= end_time={self._model_pso.end_time})")
            return False
        return True

    start_time = BaseViewModel._logged_property(
        attribute="_model_pso.start_time",
        notify_signal="startTimeChanged",
        property_type=float,
        custom_setter=_verify_start_time
    )

    # -------------------
    # end time
    # -------------------
    def _verify_end_time(self, value: float) -> bool:
        if self._model_pso.start_time >= value:
            self.logger.debug(f"Skipped 'end_time' update (value={value} <= start_time={self._model_pso.start_time})")
            return False
        return True

    end_time = BaseViewModel._logged_property(
        attribute="_model_pso.end_time",
        notify_signal="endTimeChanged",
        property_type=float,
        custom_setter=_verify_end_time
    )

    # -------------------
    # anti windup
    # -------------------
    anti_windup = BaseViewModel._logged_property(
        attribute="_model_pso.anti_windup",
        notify_signal="antiWindupChanged",
        property_type=AntiWindup
    )

    # -------------------
    # excitation_target
    # -------------------
    excitation_target = BaseViewModel._logged_property(
        attribute="_model_pso.excitation_target",
        notify_signal="excitationTargetChanged",
        property_type=ExcitationTarget
    )

    # -------------------
    # performance_index
    # -------------------
    performance_index = BaseViewModel._logged_property(
        attribute="_model_pso.performance_index",
        notify_signal="performanceIndexChanged",
        property_type=PerformanceIndex
    )

    # -------------------
    # constraint
    # -------------------
    def _verify_constraint_min(self, value: float) -> bool:
        if self._model_pso.constraint_max <= value:
            self.logger.debug(
                f"Skipped 'constraint_min' update (value={value} >= constraint_min={self._model_pso.constraint_min})")
            return False
        return True

    constraint_min = BaseViewModel._logged_property(
        attribute="_model_pso.constraint_min",
        notify_signal="constraintMinChanged",
        property_type=float,
        custom_setter=_verify_constraint_min
    )

    def _verify_constraint_max(self, value: float) -> bool:
        if self._model_pso.constraint_min >= value:
            self.logger.debug(
                f"Skipped 'constraint_max' update (value={value} <= constraint_max={self._model_pso.constraint_max})")
            return False
        return True

    constraint_max = BaseViewModel._logged_property(
        attribute="_model_pso.constraint_max",
        notify_signal="constraintMaxChanged",
        property_type=float,
        custom_setter=_verify_constraint_max
    )

    # -------------------
    # kp
    # -------------------
    def _verify_kp_min(self, value: float) -> bool:
        if self._model_pso.kp_max <= value:
            self.logger.debug(f"Skipped 'kp_min' update (value={value} >= kp_min={self._model_pso.kp_min})")
            return False
        return True

    kp_min = BaseViewModel._logged_property(
        attribute="_model_pso.kp_min",
        notify_signal="kpMinChanged",
        property_type=float,
        custom_setter=_verify_kp_min
    )

    def _verify_kp_max(self, value: float) -> bool:
        if self._model_pso.kp_min >= value:
            self.logger.debug(f"Skipped 'kp_max' update (value={value} <= kp_max={self._model_pso.kp_max})")
            return False
        return True

    kp_max = BaseViewModel._logged_property(
        attribute="_model_pso.kp_max",
        notify_signal="kpMaxChanged",
        property_type=float,
        custom_setter=_verify_kp_max
    )

    # -------------------
    # ti
    # -------------------
    def _verify_ti_min(self, value: float) -> bool:
        if self._model_pso.ti_max <= value:
            self.logger.debug(f"Skipped 'ti_min' update (value={value} >= ti_min={self._model_pso.ti_min})")
            return False
        return True

    ti_min = BaseViewModel._logged_property(
        attribute="_model_pso.ti_min",
        notify_signal="tiMinChanged",
        property_type=float,
        custom_setter=_verify_ti_min
    )

    def _verify_ti_max(self, value: float) -> bool:
        if self._model_pso.ti_min >= value:
            self.logger.debug(f"Skipped 'ti_max' update (value={value} <= ti_max={self._model_pso.ti_max})")
            return False
        return True

    ti_max = BaseViewModel._logged_property(
        attribute="_model_pso.ti_max",
        notify_signal="tiMaxChanged",
        property_type=float,
        custom_setter=_verify_ti_max
    )

    # -------------------
    # td
    # -------------------
    def _verify_td_min(self, value: float) -> bool:
        if self._model_pso.td_max <= value:
            self.logger.debug(f"Skipped 'td_min' update (value={value} >= td_min={self._model_pso.td_min})")
            return False
        return True

    td_min = BaseViewModel._logged_property(
        attribute="_model_pso.td_min",
        notify_signal="tdMinChanged",
        property_type=float,
        custom_setter=_verify_td_min
    )

    def _verify_td_max(self, value: float) -> bool:
        if self._model_pso.td_min >= value:
            self.logger.debug(f"Skipped 'td_max' update (value={value} <= td_max={self._model_pso.td_max})")
            return False
        return True

    td_max = BaseViewModel._logged_property(
        attribute="_model_pso.td_max",
        notify_signal="tdMaxChanged",
        property_type=float,
        custom_setter=_verify_td_max
    )
