from PySide6.QtCore import QObject
from typing import Iterator
from contextlib import contextmanager

class BaseViewModel(QObject):
    """
    Basis-ViewModel mit Update-Guard Funktionalität.
    Verhindert Endlosschleifen bei bidirektionalen Bindings.
    """

    def __init__(self, parent: QObject=None):
        super().__init__(parent)
        self._updating_fields: set[str] = set()

    @contextmanager
    def updating(self, field: str) -> Iterator[None]:
        """Context Manager für Update-Guard"""
        self._updating_fields.add(field)
        try:
            yield
        finally:
            self._updating_fields.discard(field)

    def check_update_allowed(self, field: str) -> bool:
        return field not in self._updating_fields