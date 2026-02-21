from PySide6.QtCore import QObject, Signal, Property
from services.controlsys import MySolver, Plant
import logging

class PlantModel(QObject):
    """Model representing a plant (transfer function) for control system simulations.

    This model maintains numerator and denominator coefficients, solver type,
    and validity state. It emits signals when properties change, enabling
    MVVM-style bindings in Qt. All significant state changes are logged.
    """

    # Signals
    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()

    def __init__(self, num: list[float] = None, den: list[float] = None,
                 solver: MySolver = MySolver.RK4, parent: QObject = None):
        """Initializes the PlantModel with optional coefficients and solver.

        Args:
            num (list[float], optional): Initial numerator coefficients. Defaults to empty list.
            den (list[float], optional): Initial denominator coefficients. Defaults to empty list.
            parent (QObject, optional): Optional Qt parent. Defaults to None.
        """
        super().__init__(parent)

        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}")

        self._num = num if num is not None else []
        self._den = den if den is not None else []

        # Check whether the provided numerator and denominator define a valid plant
        # A plant is considered valid if both lists are non-empty
        self._is_valid = self._check_validity()

        # If the coefficients are valid, create the Plant using the provided num, den, and solver
        if self._is_valid:
            self._plant = Plant(self._num, self._den)
        else:
            # If coefficients are invalid (empty), create a default Plant (1 / (s+1)) as fallback
            self._plant = Plant([1], [1, 1])

        self._logger.info(f"PlantModel initialized with initial num={self._num} and den={self._den}")

    def __repr__(self) -> str:
        return f"PlantModel(num={self._num}, den={self._den}, isValid={self._is_valid})"

    # -------------------
    # num Property
    # -------------------
    def _get_num(self) -> list[float]:
        """Returns the numerator coefficients.

        Returns:
            list[float]: Numerator coefficients.
        """
        return self._num

    def _set_num(self, value: list[float]) -> None:
        """Sets the numerator coefficients and updates state.

        Args:
            value (list[float]): New numerator coefficients.
        """
        if self._num != value:
            self._logger.debug(f"Numerator updated: {self._num} -> {value}")
            self._num = value
            self.numChanged.emit()
            self._update_state()

    num = Property(list, _get_num, _set_num, notify=numChanged)  # type: ignore[assignment]

    # -------------------
    # den Property
    # -------------------
    def _get_den(self) -> list[float]:
        """Returns the denominator coefficients.

        Returns:
            list[float]: Denominator coefficients.
        """
        return self._den

    def _set_den(self, value: list[float]) -> None:
        """Sets the denominator coefficients and updates state.

        Args:
            value (list[float]): New denominator coefficients.
        """
        if self._den != value:
            self._logger.debug(f"Denominator updated: {self._den} -> {value}")
            self._den = value
            self.denChanged.emit()
            self._update_state()

    den = Property(list, _get_den, _set_den, notify=denChanged)  # type: ignore[assignment]

    # -------------------
    # plant Property (read-only)
    # -------------------
    def get_plant(self) -> Plant:
        """Returns the internal Plant object.

        Returns:
            Plant: Current plant representation.
        """
        return self._plant

    # -------------------
    # is_valid Property
    # -------------------
    def _get_is_valid(self) -> bool:
        """Returns whether the current numerator and denominator are valid.

        Returns:
            bool: True if both numerator and denominator are non-empty.
        """
        return self._is_valid

    is_valid = Property(bool, _get_is_valid, notify=isValidChanged)   # type: ignore[assignment]

    # =========================================================
    # Helper Methods
    # =========================================================
    def _check_validity(self) -> bool:
        """Checks whether numerator and denominator are non-empty.

        Returns:
            bool: True if both numerator and denominator are set.
        """
        return len(self._den) >= len(self._num) > 0

    def _update_state(self) -> None:
        """Updates the plant and validity status based on current coefficients."""
        is_valid = self._check_validity()

        # Update the Plant object only if coefficients are valid
        if is_valid:
            self._update_plant()

        # Emit signal if validity has changed
        if is_valid != self._is_valid:
            self._logger.info(f"Validity changed: {self._is_valid} -> {is_valid}")
            self._is_valid = is_valid
            self.isValidChanged.emit()

    def _update_plant(self):
        """Creates a new Plant instance with current coefficients and solver."""
        self._plant = Plant(self._num, self._den)
        self._logger.debug(f"Plant updated: num={self._num}, den={self._den}")
