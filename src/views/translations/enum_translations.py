from typing import Callable, Type, Any
from PySide6.QtCore import QCoreApplication
from enum import Enum


from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from app_domain.functions import FunctionTypes


class ViewTitle(Enum):
    EXCITATION_TARGET = "Excitation Target"
    CLOSED_LOOP = "Closed Loop"
    REFERENCE = "Reference"
    INPUT_DISTURBANCE = "Input Disturbance"
    MEASUREMENT_DISTURBANCE = "Measurement Disturbance"


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
            ViewTitle: self._view_title_label,
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
        }

    @staticmethod
    def _view_title_label() -> dict[ViewTitle, str]:
        """Return translated labels for Titles enum."""
        return {
            ViewTitle.EXCITATION_TARGET: QCoreApplication.translate("ControlEnums", "Excitation Target"),
            ViewTitle.CLOSED_LOOP: QCoreApplication.translate("ControlEnums", "Closed Loop"),
            ViewTitle.REFERENCE: QCoreApplication.translate("ControlEnums", "Reference"),
            ViewTitle.INPUT_DISTURBANCE: QCoreApplication.translate("ControlEnums", "Input Disturbance"),
            ViewTitle.MEASUREMENT_DISTURBANCE: QCoreApplication.translate("ControlEnums", "Measurement Disturbance"),
        }
