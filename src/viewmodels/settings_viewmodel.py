from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Property, QByteArray, Slot

from app_domain.controlsys import MySolver
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from models import SettingsModel


class SettingsViewModel(BaseViewModel):
    solverChanged = Signal()
    timeStepChanged = Signal()
    psoIterationsChanged = Signal()
    psoParticleChanged = Signal()

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        BaseViewModel.__init__(self, parent)

        self._settings = settings

    def _get_solver(self) -> MySolver:
        self.logger.debug(f"Getter 'solver' called (value={self._settings.get_solver()})")
        return self._settings.get_solver()

    def _set_solver(self, solver: MySolver):
        self.logger.debug(f"Setter 'solver' called (value={solver})")
        self._settings.set_solver(solver)

    solver = Property(MySolver, _get_solver, _set_solver, notify=solverChanged)

    def _get_time_step(self) -> float:
        self.logger.debug(f"Getter 'time_step' called (value={self._settings.get_time_step()})")
        return self._settings.get_time_step()

    def _set_time_step(self, value: float):
        self.logger.debug(f"Setter 'time_step' called (value={value})")
        self._settings.set_time_step(value)

    time_step = Property(float, _get_time_step, _set_time_step, notify=timeStepChanged)

    def _get_pso_iterations(self) -> int:
        self.logger.debug(f"Getter 'pso_iterations' called (value={self._settings.get_pso_iterations()})")
        return self._settings.get_pso_iterations()

    def _set_pso_iterations(self, value: int):
        self.logger.debug(f"Setter 'pso_iterations' called (value={value})")
        self._settings.set_pso_iterations(value)

    pso_iterations = Property(int, _get_pso_iterations, _set_pso_iterations, notify=psoIterationsChanged)

    def _get_pso_particle(self) -> int:
        self.logger.debug(f"Getter 'pso_particle' called (value={self._settings.get_pso_particle()})")
        return self._settings.get_pso_particle()

    def _set_pso_particle(self, value: int):
        self.logger.debug(f"Setter 'pso_particle' called (value={value})")
        self._settings.set_pso_particle(value)

    pso_particle = Property(int, _get_pso_particle, _set_pso_particle, notify=psoParticleChanged)

    @Slot()
    def get_window_geometry(self) -> QByteArray:
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
