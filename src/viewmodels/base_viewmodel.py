from PySide6.QtCore import QObject
from typing import Iterator
from contextlib import contextmanager
import logging

class BaseViewModel(QObject):
    """
    Basis-ViewModel mit Update-Guard Funktionalität.
    Verhindert Endlosschleifen bei bidirektionalen Bindings.
    """

    def __init__(self, parent: QObject=None):
        super().__init__(parent)
        self._updating_fields: set[str] = set()

        self._logger = logging.getLogger(f"ViewModel.{self.__class__.__name__}.{id(self)}")

    def _connect_signals(self) -> None:
        raise NotImplementedError

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