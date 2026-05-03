import inspect
from typing import Callable, Type, Any
from PySide6.QtCore import QCoreApplication
from enum import Enum

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex, MySolver, ControllerType
from app_domain.functions import FunctionTypes
from app_types import LanguageType, ThemeType, PlotLabels, NavLabels, PerformanceIndexDescription, validate_enum_mapping


def register_translation(enum_type):
    """Decorator to register a method as a translation handler for a given enum type.

    This decorator attaches metadata to the decorated function indicating
    which enum type it is responsible for. The metadata can later be used
    to automatically build a registry of enum-to-function mappings.

    Args:
        enum_type: The enum class that the decorated function will handle.

    Returns:
        A decorator that attaches the enum type metadata to the function
        and returns the function unchanged.

    Example:
        ```
        @register_translation(MyEnum)
        def translate_my_enum(self, value: MyEnum) -> str:
            return "some label"
        ```
    """

    def decorator(func):
        """Attach enum type metadata to the function.

        Args:
            func: The function to decorate.

        Returns:
            The same function with an added `register_for` attribute.
        """
        func.register_for = enum_type
        return func

    return decorator


class Translation:
    """Provides translated display labels for supported enum types.

    The class acts as a callable dispatcher that maps enum types
    to their corresponding translation dictionaries.
    """

    def __init__(self) -> None:
        validate_enum_mapping(PerformanceIndex, PerformanceIndexDescription)
        self._registry: dict[Type[Any], Callable[[Enum], str]] = {}

        # automatically find and register methods
        for _, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "register_for"):
                enum_type = method.register_for
                self._registry[enum_type] = method


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
            raise ValueError(f"No translation registered for enum type: {type(value).__name__}")

    # ------------------------------------------------------------------
    # Individual enum translation mappings
    # ------------------------------------------------------------------
    @register_translation(AntiWindup)
    def _anti_windup(self, value: Enum) -> str:
        """Return translated label for AntiWindup enum."""
        match value:
            case AntiWindup.CLAMPING:
                return QCoreApplication.translate("ControlEnums", "Clamping")
            case AntiWindup.CONDITIONAL:
                return QCoreApplication.translate("ControlEnums", "Conditional")
            case AntiWindup.BACKCALCULATION:
                return QCoreApplication.translate("ControlEnums", "Backcalculation")
            case _:
                raise ValueError(f"No translation registered for enum type: {value}")

    @register_translation(ExcitationTarget)
    def _excitation_target(self, value: Enum) -> str:
        """Return translated label for ExcitationTarget enum."""
        match value:
            case ExcitationTarget.REFERENCE:
                return QCoreApplication.translate("ControlEnums", "Reference r")
            case ExcitationTarget.INPUT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Input Disturbance l")
            case ExcitationTarget.MEASUREMENT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "Measurement Disturbance n")
            case _:
                raise ValueError(f"No translation registered for enum type: {value}")

    @register_translation(PerformanceIndex)
    def _performance_index(self, value: Enum) -> str:
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
                raise ValueError(f"No translation registered for enum type: {value}")

    @register_translation(PerformanceIndexDescription)
    def _performance_index_description(self, value: Enum) -> str:
        """Return translated description for PerformanceIndex enum."""
        match value:
            case PerformanceIndexDescription.ITAE:
                return QCoreApplication.translate("ControlEnums", "Integral of Time-weighted Absolute Error")
            case PerformanceIndexDescription.IAE:
                return QCoreApplication.translate("ControlEnums", "Integral of Absolute Error")
            case PerformanceIndexDescription.ITSE:
                return QCoreApplication.translate("ControlEnums", "Integral of Time-weighted Squared Error")
            case PerformanceIndexDescription.ISE:
                return QCoreApplication.translate("ControlEnums", "Integral of Squared Error")
            case _:
                raise ValueError(f"No translation registered for enum type: {value}")

    @register_translation(FunctionTypes)
    def _function_type(self, value: Enum) -> str:
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
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(NavLabels)
    def _nav_labels(self, value: Enum) -> str:
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
            case NavLabels.DATA_MANAGEMENT:
                return QCoreApplication.translate("ControlEnums", "Data Management")
            case NavLabels.HELP:
                return QCoreApplication.translate("ControlEnums", "Help")
            case NavLabels.SETTINGS:
                return QCoreApplication.translate("ControlEnums", "Settings")
            case _:
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(PlotLabels)
    def _plot_labels(self, value: Enum) -> str:
        """Return translated label for PlotLabels enum."""
        match value:
            case PlotLabels.PLANT:
                return QCoreApplication.translate("ControlEnums", "plant")
            case PlotLabels.FUNCTION:
                return QCoreApplication.translate("ControlEnums", "function")
            case PlotLabels.CLOSED_LOOP:
                return QCoreApplication.translate("ControlEnums", "y_closed_loop")
            case PlotLabels.CONTROL_SIGNAL:
                return QCoreApplication.translate("ControlEnums", "u_control_signal")
            case PlotLabels.REFERENCE:
                return QCoreApplication.translate("ControlEnums", "r_reference")
            case PlotLabels.INPUT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "l_input_disturbance")
            case PlotLabels.MEASUREMENT_DISTURBANCE:
                return QCoreApplication.translate("ControlEnums", "n_measurement_disturbance")
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
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(MySolver)
    def _my_solver(self, value: Enum) -> str:
        """Return translated label for MySolver enum."""
        match value:
            case MySolver.RK4:
                return QCoreApplication.translate("ControlEnums", "RK4")
            case _:
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(LanguageType)
    def _language_type(self, value: Enum) -> str:
        """Return translated label for LanguageType enum."""
        match value:
            case LanguageType.ENGLISH:
                return QCoreApplication.translate("ControlEnums", "English")
            case LanguageType.GERMAN:
                return QCoreApplication.translate("ControlEnums", "German")
            case _:
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(ThemeType)
    def _theme_type(self, value: Enum) -> str:
        """Return translated label for ThemeType enum."""
        match value:
            case ThemeType.LIGHT:
                return QCoreApplication.translate("ControlEnums", "Light")
            case ThemeType.DARK:
                return QCoreApplication.translate("ControlEnums", "Dark")
            case _:
                raise ValueError(f"No translation registered for enum value: {value}")

    @register_translation(ControllerType)
    def _controller_type(self, value: Enum) -> str:
        """Return translated label for ControllerType enum."""
        match value:
            case ControllerType.PI:
                return QCoreApplication.translate("ControlEnums", "PI")
            case ControllerType.PID:
                return QCoreApplication.translate("ControlEnums", "PID")
            case ControllerType.FFPID:
                return QCoreApplication.translate("ControlEnums", "FFPID")
            case _:
                raise ValueError(f"No translation registered for enum value: {value}")
