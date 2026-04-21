from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QByteArray, Slot

from app_domain.controlsys import MySolver
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from models import SettingsModel


class SettingsViewModel(BaseViewModel):
    solverChanged = Signal()
    timeStepChanged = Signal()

    psoSwarmSizeChanged = Signal()
    psoRepeatRunsChanged = Signal()
    psoRandomnessChanged = Signal()
    psoU1Changed = Signal()
    psoU2Changed = Signal()
    psoInitialRangeStartChanged = Signal()
    psoInitialRangeEndChanged = Signal()
    psoInitialSwarmSpanChanged = Signal()
    psoMinNeighborsFractionChanged = Signal()
    psoMaxStallChanged = Signal()
    psoMaxIterChanged = Signal()
    psoStallWindowsRequiredChanged = Signal()
    psoSpaceFactorChanged = Signal()
    psoConvergenceFactorChanged = Signal()

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        BaseViewModel.__init__(self, parent)
        self._settings = settings

    solver: MySolver = LoggedProperty(
        path="_settings.solver",
        signal="solverChanged",
        typ=MySolver,
    )

    time_step: float = LoggedProperty(
        path="_settings.time_step",
        signal="timeStepChanged",
        typ=float,
    )

    pso_swarm_size: int = LoggedProperty(
        path="_settings.pso_swarm_size",
        signal="psoSwarmSizeChanged",
        typ=int,
    )

    pso_repeat_runs: int = LoggedProperty(
        path="_settings.pso_repeat_runs",
        signal="psoRepeatRunsChanged",
        typ=int,
    )

    pso_randomness: float = LoggedProperty(
        path="_settings.pso_randomness",
        signal="psoRandomnessChanged",
        typ=float,
    )

    pso_u1: float = LoggedProperty(
        path="_settings.pso_u1",
        signal="psoU1Changed",
        typ=float,
    )

    pso_u2: float = LoggedProperty(
        path="_settings.pso_u2",
        signal="psoU2Changed",
        typ=float,
    )

    pso_initial_range_start: float = LoggedProperty(
        path="_settings.pso_initial_range_start",
        signal="psoInitialRangeStartChanged",
        typ=float,
    )

    pso_initial_range_end: float = LoggedProperty(
        path="_settings.pso_initial_range_end",
        signal="psoInitialRangeEndChanged",
        typ=float,
    )

    pso_initial_swarm_span: int = LoggedProperty(
        path="_settings.pso_initial_swarm_span",
        signal="psoInitialSwarmSpanChanged",
        typ=int,
    )

    pso_min_neighbors_fraction: float = LoggedProperty(
        path="_settings.pso_min_neighbors_fraction",
        signal="psoMinNeighborsFractionChanged",
        typ=float,
    )

    pso_max_stall: int = LoggedProperty(
        path="_settings.pso_max_stall",
        signal="psoMaxStallChanged",
        typ=int,
    )

    pso_max_iter: int = LoggedProperty(
        path="_settings.pso_max_iter",
        signal="psoMaxIterChanged",
        typ=int,
    )

    pso_stall_windows_required: int = LoggedProperty(
        path="_settings.pso_stall_windows_required",
        signal="psoStallWindowsRequiredChanged",
        typ=int,
    )

    pso_space_factor: float = LoggedProperty(
        path="_settings.pso_space_factor",
        signal="psoSpaceFactorChanged",
        typ=float,
    )

    pso_convergence_factor: float = LoggedProperty(
        path="_settings.pso_convergence_factor",
        signal="psoConvergenceFactorChanged",
        typ=float,
    )

    @Slot()
    def get_window_geometry(self) -> QByteArray | None:
        self.logger.debug(f"Getter 'window_geometry' called")
        return self._settings.get_window_geometry()

    @Slot(object)
    def set_window_geometry(self, geometry: QByteArray) -> None:
        self.logger.debug(f"Setter 'window_geometry' called (value={geometry})")
        self._settings.set_window_geometry(geometry)

    @Slot()
    def get_window_maximized(self) -> bool:
        self.logger.debug(f"Getter 'window_maximized' called")
        return self._settings.get_window_maximized()

    @Slot(bool)
    def set_window_maximized(self, value: bool) -> None:
        self.logger.debug(f"Setter 'window_maximized' called (value={value})")
        self._settings.set_window_maximized(value)

    @Slot()
    def get_nav_collapsed(self) -> bool:
        self.logger.debug("Getter 'nav_collapsed' called")
        return self._settings.get_nav_collapsed()

    @Slot(bool)
    def set_nav_collapsed(self, value: bool) -> None:
        self.logger.debug(f"Setter 'nav_collapsed' called (value={value})")
        self._settings.set_nav_collapsed(value)

    @Slot()
    def reset_to_defaults(self) -> None:
        self.logger.debug("Resetting settings to defaults")
        self._settings.reset_pso_settings()
        self.refresh_from_model()

    @Slot()
    def refresh_from_model(self) -> None:
        self.solverChanged.emit()
        self.timeStepChanged.emit()

        self.psoSwarmSizeChanged.emit()
        self.psoRepeatRunsChanged.emit()
        self.psoRandomnessChanged.emit()
        self.psoU1Changed.emit()
        self.psoU2Changed.emit()
        self.psoInitialRangeStartChanged.emit()
        self.psoInitialRangeEndChanged.emit()
        self.psoInitialSwarmSpanChanged.emit()
        self.psoMinNeighborsFractionChanged.emit()
        self.psoMaxStallChanged.emit()
        self.psoMaxIterChanged.emit()
        self.psoStallWindowsRequiredChanged.emit()
        self.psoSpaceFactorChanged.emit()
        self.psoConvergenceFactorChanged.emit()
