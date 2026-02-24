import logging

from PySide6.QtCore import QObject, Signal, Slot, Property

from app_domain.functions import BaseFunction, FunctionTypes


class FunctionModel(QObject):
    """MVVM-style model holding function, input t, and output y.

    Attributes:
        functionChanged: Signal emitted when the function changes.
        parameterChanged: Signal emitted when the parameter changes.
        _selected_function: Current BaseFunction instance.
        _func_thread: Thread computing function outputs.
    """

    functionChanged = Signal()
    parameterChanged = Signal(str)

    def __init__(self, function: BaseFunction, parent: QObject = None):
        """Initialize the FunctionModel."""
        super().__init__(parent)
        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FunctionModel initialized")

        self._selected_function: BaseFunction = function
        self._func_thread = None
        self._logger.info("Default function set: %s", type(self._selected_function).__name__)

    @Slot(FunctionTypes)
    def set_selected_function(self, function: FunctionTypes) -> None:
        """Change the current function by name.

        Args:
            function: Name of the function as string (matches Functions enum).
        """
        try:
            func_class = function.value
            if type(self._selected_function).__name__ != func_class.__name__:
                self._selected_function = func_class()
                self._logger.info("Function changed to: %s", type(self._selected_function).__name__)
                self.functionChanged.emit()
        except KeyError:
            self._logger.error("Function %s not found", function)

    def _get_selected_function(self) -> BaseFunction:
        """Getter for the function property."""
        return self._selected_function

    selected_function = Property(BaseFunction, _get_selected_function, notify=functionChanged)  # type: ignore[assignment]

    @Slot(str, float)
    def update_param_value(self, key: str, value: float) -> None:
        """
        Update the value of a function parameter if it has changed.

        Args:
            key (str): The name of the parameter to update.
            value (float): The new value to set.
        """
        # Get current parameter value
        current_value = self._selected_function.get_param_value(key)

        # Only update if the value actually changed
        if value != current_value:
            self._logger.info("Parameter '%s' changed from %f to %f", key, current_value, value)

            self._selected_function.update_param_value(key, value)

            # Notify observers that a parameter has changed
            self.parameterChanged.emit(key)
