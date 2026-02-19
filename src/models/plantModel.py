from PySide6.QtCore import QObject, Signal, Property

from services.controlsys import MySolver, Plant

class PlantModel(QObject):

    numChanged = Signal()
    denChanged = Signal()
    validityChanged = Signal()

    def __init__(self, parent: QObject=None):
        super().__init__(parent)

        self._num: list[float] = []
        self._den: list[float] = []
        self._solver: MySolver = MySolver.RK4

        self._plant: Plant

        self._is_valid: bool = False

    def _get_num(self) -> list[float]:
        return self._num

    def _set_num(self, num: list[float]) -> None:
        self._num = num

        # is num valid
        value = self._is_valid and self._check_validity(num)
        if value != self._is_valid:
            self.numChanged.emit()

    num = Property(list, _get_num, _set_num, notify=numChanged)

    def _get_den(self) -> list[float]:
        return self._den

    def _set_den(self, den: list[float]) -> None:
        self._den = den

        # is den valid
        value = self._is_valid and self._check_validity(den)
        if value != self._is_valid:
            self.numChanged.emit()

    den = Property(list, _get_den, _set_den, notify=denChanged)

    def _get_is_valid(self) -> bool:
        return self._is_valid

    is_valid = Property(bool, _get_is_valid, notify=validityChanged)

    @staticmethod
    def _check_validity(lst: list[float]) -> bool:
        return len(lst) != 0
