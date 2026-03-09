from typing import Callable, Type, Any
from PySide6.QtCore import QCoreApplication
from enum import Enum


from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from app_domain.functions import FunctionTypes


class NavLabels(Enum):
    PLANT = "Plant"
    EXCITATION_FUNCTION = "Excitation Function"
    CONTROLLER = "Controller"
    PSO_PARAMETER = "PSO Parameter"
    EVALUATION = "Evaluation"
    SIMULATION = "Simulation"


class PlotLabels(Enum):
    PLANT = "Plant"
    FUNCTION = "Function"
    CLOSED_LOOP = "Closed Loop"
    CONTROL_SIGNAL = "Control Signal"
    REFERENCE = "Reference"
    INPUT_DISTURBANCE = "Input Disturbance"
    MEASUREMENT_DISTURBANCE = "Measurement Disturbance"
    G = "G"
    C = "C"
    L = "L"
    S = "S"
    T = "T"


assert len(set(e.value for e in PlotLabels)) == len(PlotLabels), "Duplicate values in PlotLabels!"


class Translation:
    """Provides translated display labels for supported enum types.

    The class acts as a callable dispatcher that maps enum types
    to their corresponding translation dictionaries.
    """

    def __init__(self) -> None:

        # Central registry of enum type -> translation method
        self._registry: dict[Type[Any], Callable[[], dict[Any, str]]] = {
            AntiWindup: self._anti_windup_label,
            ExcitationTarget: self._excitation_target_label,
            FunctionTypes: self._function_type_label,
            PerformanceIndex: self._performance_index_label,
            NavLabels: self._nav_label,
            PlotLabels: self._plot_labels,
        }

    def __call__(self, enum_type: Type[Any]) -> dict[Any, str]:
        """Return the translation dictionary for a given enum type.

        Args:
            enum_type: Enum class (not enum instance).

        Returns:
            Dictionary mapping enum members to translated strings.

        Raises:
            NotImplementedError: If enum type is not registered.
        """
        try:
            return self._registry[enum_type]().copy()
        except KeyError:
            raise NotImplementedError(
                f"No translation registered for enum type: {enum_type}"
            ) from None

    # ------------------------------------------------------------------
    # Individual enum translation mappings
    # ------------------------------------------------------------------
    @staticmethod
    def _anti_windup_label() -> dict[AntiWindup, str]:
        """Return translated labels for AntiWindup enum."""
        return {
            AntiWindup.CLAMPING: QCoreApplication.translate("ControlEnums", "Clamping"),
            AntiWindup.CONDITIONAL: QCoreApplication.translate("ControlEnums", "Conditional"),
        }

    @staticmethod
    def _excitation_target_label() -> dict[ExcitationTarget, str]:
        """Return translated labels for ExcitationTarget enum."""
        return {
            ExcitationTarget.REFERENCE: QCoreApplication.translate("ControlEnums", "Reference"),
            ExcitationTarget.INPUT_DISTURBANCE: QCoreApplication.translate("ControlEnums", "Input Disturbance"),
            ExcitationTarget.MEASUREMENT_DISTURBANCE: QCoreApplication.translate("ControlEnums",
                                                                                 "Measurement Disturbance"),
        }

    @staticmethod
    def _performance_index_label() -> dict[PerformanceIndex, str]:
        """Return translated labels for PerformanceIndex enum."""
        return {
            PerformanceIndex.ITAE: QCoreApplication.translate("ControlEnums", "ITAE"),
            PerformanceIndex.IAE: QCoreApplication.translate("ControlEnums", "IAE"),
            PerformanceIndex.ITSE: QCoreApplication.translate("ControlEnums", "ITSE"),
            PerformanceIndex.ISE: QCoreApplication.translate("ControlEnums", "ISE"),
        }

    @staticmethod
    def _function_type_label() -> dict[FunctionTypes, str]:
        """Return translated labels for FunctionTypes enum."""
        return {
            FunctionTypes.NULL: QCoreApplication.translate("ControlEnums", "Null"),
            FunctionTypes.STEP: QCoreApplication.translate("ControlEnums", "step"),
            FunctionTypes.SINE: QCoreApplication.translate("ControlEnums", "sine"),
            FunctionTypes.COSINE: QCoreApplication.translate("ControlEnums", "cosine"),
            FunctionTypes.RECTANGULAR: QCoreApplication.translate("ControlEnums", "rectangle"),
        }

    @staticmethod
    def _nav_label() -> dict[NavLabels, str]:
        """Return translated labels for NavLabel enum."""
        return {
            NavLabels.PLANT: QCoreApplication.translate("ControlEnums", "Plant"),
            NavLabels.EXCITATION_FUNCTION: QCoreApplication.translate("ControlEnums", "Excitation Function"),
            NavLabels.CONTROLLER: QCoreApplication.translate("ControlEnums", "Controller"),
            NavLabels.PSO_PARAMETER: QCoreApplication.translate("ControlEnums", "PSO Parameter"),
            NavLabels.EVALUATION: QCoreApplication.translate("ControlEnums", "Evaluation"),
            NavLabels.SIMULATION: QCoreApplication.translate("ControlEnums", "Simulation"),
        }

    @staticmethod
    def _plot_labels() -> dict[PlotLabels, str]:
        """Return translated labels for PlotLabels enum."""
        return {
            PlotLabels.PLANT: QCoreApplication.translate("ControlEnums", "Plant"),
            PlotLabels.FUNCTION: QCoreApplication.translate("ControlEnums", "Function"),
            PlotLabels.CLOSED_LOOP: QCoreApplication.translate("ControlEnums", "Closed Loop"),
            PlotLabels.CONTROL_SIGNAL: QCoreApplication.translate("ControlEnums", "Control Signal"),
            PlotLabels.REFERENCE: QCoreApplication.translate("ControlEnums", "Reference"),
            PlotLabels.INPUT_DISTURBANCE: QCoreApplication.translate("ControlEnums", "Input Disturbance"),
            PlotLabels.MEASUREMENT_DISTURBANCE: QCoreApplication.translate("ControlEnums", "Measurement Disturbance"),
            PlotLabels.G: QCoreApplication.translate("ControlEnums", "G_plant"),
            PlotLabels.C: QCoreApplication.translate("ControlEnums", "C_controller"),
            PlotLabels.L: QCoreApplication.translate("ControlEnums", "L_open_loop"),
            PlotLabels.S: QCoreApplication.translate("ControlEnums", "S_sensitivity"),
            PlotLabels.T: QCoreApplication.translate("ControlEnums", "T_complement_sensitivity"),
        }
