from PySide6.QtCore import QObject, Signal, Property
from services.controlsys import MySolver, Plant

class PlantModel(QObject):
    """Model representing a plant (transfer function) for control system simulations.

    This model maintains numerator and denominator coefficients, solver type,
    and validity state. It emits signals when properties change, enabling
    MVVM-style bindings in Qt.
    """

    # Signals for property change notifications
    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()
    solverChanged = Signal()

    def __init__(self, parent: QObject = None):
        """Initializes the PlantModel with default values.

        Args:
            parent (QObject, optional): Optional Qt parent object. Defaults to None.
        """
        super().__init__(parent)

        # Numerator and denominator coefficients
        self._num: list[float] = []
        self._den: list[float] = []

        # Numerical solver for plant simulation
        self._solver: MySolver = MySolver.RK4

        # Internal plant representation
        self._plant: Plant = Plant([1], [1, 1], self._solver)

        # Indicates whether the current coefficients are valid
        self._is_valid: bool = False

    # =========================================================
    # Properties
    # =========================================================

    # -------------------
    # num
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
            self._num = value
            self.numChanged.emit()
            self._update_state()

    num = Property(list, _get_num, _set_num, notify=numChanged)  # type: ignore[assignment]

    # -------------------
    # den
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
            self._den = value
            self.denChanged.emit()
            self._update_state()

    den = Property(list, _get_den, _set_den, notify=denChanged)  # type: ignore[assignment]

    # -------------------
    # plant
    # -------------------
    def get_plant(self) -> Plant:
        """Returns the internal Plant object.

        Returns:
            Plant: Current plant representation.
        """
        return self._plant

    # -------------------
    # Validity
    # -------------------
    def is_valid(self) -> bool:
        """Returns whether the current numerator and denominator are valid.

        Returns:
            bool: True if both numerator and denominator are non-empty.
        """
        return self._is_valid

    # -------------------
    # Solver
    # -------------------
    def set_solver(self, value: MySolver) -> None:
        """Sets the numerical solver and updates the plant state.

        Args:
            value (MySolver): New solver to use for the plant.
        """
        if self._solver != value:
            self._solver = value
            self.solverChanged.emit()
            self._update_state()

    # =========================================================
    # Helper Methods
    # =========================================================
    def _check_validity(self) -> bool:
        """Checks whether numerator and denominator are non-empty.

        Returns:
            bool: True if both numerator and denominator are set.
        """
        return len(self._num) != 0 and len(self._den) != 0

    def _update_state(self) -> None:
        """Updates the plant and validity status based on current coefficients."""
        is_valid = self._check_validity()

        # Update the Plant object only if coefficients are valid
        if is_valid:
            self._update_plant()

        # Emit signal if validity has changed
        if is_valid != self._is_valid:
            self._is_valid = is_valid
            self.isValidChanged.emit()

    def _update_plant(self):
        """Creates a new Plant instance with current coefficients and solver."""
        self._plant = Plant(self._num, self._den, self._solver)
