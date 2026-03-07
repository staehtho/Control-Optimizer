from contextlib import contextmanager
import logging
from typing import Iterator

from PySide6.QtCore import QObject, Signal

from .types import FieldType


class BaseViewModel(QObject):
    """Base ViewModel with an update-guard to avoid feedback loops."""

    validationFailed = Signal(FieldType, str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._updating_fields: set[str] = set()
        self.logger = logging.getLogger(f"ViewModel.{self.__class__.__name__}.{id(self)}")

    def _connect_signals(self) -> None:
        raise NotImplementedError

    @contextmanager
    def updating(self, field: str) -> Iterator[None]:
        """Temporarily mark a field as updating to break feedback loops."""
        self._updating_fields.add(field)
        try:
            yield
        finally:
            self._updating_fields.discard(field)

    def check_update_allowed(self, field: str) -> bool:
        return field not in self._updating_fields
