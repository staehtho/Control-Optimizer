from PySide6.QtCore import QObject, Signal

from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from models import ModelContainer, PsoConfigurationModel, SettingsModel
from .base_viewmodel import BaseViewModel


class PsoConfigurationViewModel(BaseViewModel):

    startTimeChanged = Signal()
    endTimeChanged = Signal()
    excitationTargetChanged = Signal()
    performanceIndexChanged = Signal()
    kpMinChanged = Signal()
    kpMaxChanged = Signal()
    tiMinChanged = Signal()
    tiMaxChanged = Signal()
    tdMinChanged = Signal()
    tdMaxChanged = Signal()

    def __init__(self, model_container: ModelContainer, parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_function = model_container.model_function
        self._model_pso: PsoConfigurationModel = model_container.model_pso
        self._settings: SettingsModel = model_container.model_settings

        self._connect_signals()

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

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
    def _verify_ti_min(self, value: float) -> float | None:
        if value == 0:
            value = 1e-9

        if self._model_pso.ti_max <= value:
            self.logger.debug(
                f"Skipped 'ti_min' update (value={value} >= ti_max={self._model_pso.ti_max})"
            )
            return None

        return value

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
