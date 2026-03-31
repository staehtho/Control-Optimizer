from typing import Callable, Type, Any
from PySide6.QtCore import QCoreApplication
from enum import Enum

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex, MySolver
from app_domain.functions import FunctionTypes
from app_types import LanguageType, ThemeType, PlotLabels, NavLabels


class Translation:
    """Provides translated display labels for supported enum types.

    The class acts as a callable dispatcher that maps enum types
    to their corresponding translation dictionaries.
    """

    def __init__(self) -> None:

        # Central registry of enum type -> translation method
        self._registry: dict[Type[Any], Callable[[Enum], str]] = {
            AntiWindup: self._anti_windup_label,
            ExcitationTarget: self._excitation_target_label,
            FunctionTypes: self._function_type_label,
            PerformanceIndex: self._performance_index_label,
            NavLabels: self._nav_label,
            PlotLabels: self._plot_labels,
            MySolver: self._solver_label,
            LanguageType: self._language_type_label,
            ThemeType: self._theme_type_label
        }

    def __call__(self, value: Enum) -> str:
        """Return the translated string for a given enum value.

        Args:
            value: Enum member to translate.

        Returns:
            The translated string corresponding to the given enum value.

        Raises:
            NotImplementedError: If no translation function is registered
                for the enum type of the given value.
        """
        try:
            return self._registry[type(value)](value)
        except KeyError:
            raise NotImplementedError(f"No translation registered for enum type: {type(value).__name__}")

    # ------------------------------------------------------------------
    # Individual enum translation mappings
    # ------------------------------------------------------------------
    @staticmethod
    def _anti_windup_label(value: Enum) -> str:
        """Return translated label for AntiWindup enum."""
        match value:
            case AntiWindup.CLAMPING:
                return QCoreApplication.translate("ControlEnums", "Clamping")
            case AntiWindup.CONDITIONAL:
                return QCoreApplication.translate("ControlEnums", "Conditional")
            case AntiWindup.BACKCALCULATION:
                return QCoreApplication.translate("ControlEnums", "Backcalculation")
            case _:
                raise NotImplementedError(f"No translation registered for enum type: {value}")

    @staticmethod
    def _excitation_target_label(value: Enum) -> str:
        """Return translated label for ExcitationTarget enum."""
        match value:
            case ExcitationTarget.REFERENCE:
                return QCoreApplication.translate("ControlEnums", "Reference")
            case ExcitationTarget.INPUT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Input Disturbance")
            case ExcitationTarget.MEASUREMENT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Measurement Disturbance")
            case _:
                raise NotImplementedError(f"No translation registered for enum type: {value}")

    @staticmethod
    def _performance_index_label(value: Enum) -> str:
        """Return translated label for PerformanceIndex enum."""
        match value:
            case PerformanceIndex.ITAE:
                return QCoreApplication.translate("ControlEnums", "ITAE")
            case PerformanceIndex.IAE:
                return QCoreApplication.translate("ControlEnums", "IAE")
            case PerformanceIndex.ITSE:
                return QCoreApplication.translate("ControlEnums", "ITSE")
            case PerformanceIndex.ISE:
                return QCoreApplication.translate("ControlEnums", "ISE")
            case _:
                raise NotImplementedError(f"No translation registered for enum type: {value}")

    @staticmethod
    def _function_type_label(value: Enum) -> str:
        """Return translated label for FunctionTypes enum."""
        match value:
            case FunctionTypes.NULL:
                return QCoreApplication.translate("ControlEnums", "Null")
            case FunctionTypes.STEP:
                return QCoreApplication.translate("ControlEnums", "Step")
            case FunctionTypes.SINE:
                return QCoreApplication.translate("ControlEnums", "Sine")
            case FunctionTypes.COSINE:
                return QCoreApplication.translate("ControlEnums", "Cosine")
            case FunctionTypes.RECTANGULAR:
                return QCoreApplication.translate("ControlEnums", "Rectangle")
            case FunctionTypes.BROWNIAN_NOISE:
                return QCoreApplication.translate("ControlEnums", "BrownianNoise")
            case FunctionTypes.PINK_NOISE:
                return QCoreApplication.translate("ControlEnums", "PinkNoise")
            case FunctionTypes.WHITE_NOISE:
                return QCoreApplication.translate("ControlEnums", "WhiteNoise")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")

    @staticmethod
    def _nav_label(value: Enum) -> str:
        """Return translated label for NavLabels enum."""
        match value:
            case NavLabels.PLANT:
                return QCoreApplication.translate("ControlEnums", "Plant")
            case NavLabels.EXCITATION_FUNCTION:
                return QCoreApplication.translate("ControlEnums", "Excitation Function")
            case NavLabels.CONTROLLER:
                return QCoreApplication.translate("ControlEnums", "Controller")
            case NavLabels.PSO_PARAMETER:
                return QCoreApplication.translate("ControlEnums", "PSO Parameter")
            case NavLabels.EVALUATION:
                return QCoreApplication.translate("ControlEnums", "Evaluation")
            case NavLabels.SIMULATION:
                return QCoreApplication.translate("ControlEnums", "Simulation")
            case NavLabels.SETTINGS:
                return QCoreApplication.translate("ControlEnums", "Settings")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")

    @staticmethod
    def _plot_labels(value: Enum) -> str:
        """Return translated label for PlotLabels enum."""
        match value:
            case PlotLabels.PLANT:
                return QCoreApplication.translate("ControlEnums", "Plant")
            case PlotLabels.FUNCTION:
                return QCoreApplication.translate("ControlEnums", "Function")
            case PlotLabels.CLOSED_LOOP:
                return QCoreApplication.translate("ControlEnums", "Closed Loop")
            case PlotLabels.CONTROL_SIGNAL:
                return QCoreApplication.translate("ControlEnums", "Control Signal")
            case PlotLabels.REFERENCE:
                return QCoreApplication.translate("ControlEnums", "Reference")
            case PlotLabels.INPUT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Input Disturbance")
            case PlotLabels.MEASUREMENT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Measurement Disturbance")
            case PlotLabels.G:
                return QCoreApplication.translate("ControlEnums", "G_plant")
            case PlotLabels.C:
                return QCoreApplication.translate("ControlEnums", "C_controller")
            case PlotLabels.L:
                return QCoreApplication.translate("ControlEnums", "L_open_loop")
            case PlotLabels.T:
                return QCoreApplication.translate("ControlEnums", "T_closed_loop")
            case PlotLabels.S:
                return QCoreApplication.translate("ControlEnums", "S_sensitivity")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")

    @staticmethod
    def _solver_label(value: Enum) -> str:
        """Return translated label for MySolver enum."""
        match value:
            case MySolver.RK4:
                return QCoreApplication.translate("ControlEnums", "RK4")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")

    @staticmethod
    def _language_type_label(value: Enum) -> str:
        """Return translated label for LanguageType enum."""
        match value:
            case LanguageType.ENGLISH:
                return QCoreApplication.translate("ControlEnums", "English")
            case LanguageType.GERMAN:
                return QCoreApplication.translate("ControlEnums", "German")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")

    @staticmethod
    def _theme_type_label(value: Enum) -> str:
        """Return translated label for ThemeType enum."""
        match value:
            case ThemeType.LIGHT:
                return QCoreApplication.translate("ControlEnums", "Light")
            case ThemeType.DARK:
                return QCoreApplication.translate("ControlEnums", "Dark")
            case _:
                raise NotImplementedError(f"No translation registered for enum value: {value}")


