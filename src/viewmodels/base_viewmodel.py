from PySide6.QtCore import QObject, Property
from typing import Iterator, Any, Optional, Callable
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

        self.logger = logging.getLogger(f"ViewModel.{self.__class__.__name__}.{id(self)}")

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

    @staticmethod
    def _logged_property(
            attribute: str,
            notify_signal: str,
            property_type: Any,
            custom_setter: Optional[Callable[..., bool]] = None,
    ) -> Property:

        def getter(instance) -> Any:
            attr = instance
            for attr_name in attribute.split("."):
                attr = getattr(attr, attr_name)
            value = attr
            instance.logger.debug(f"Getter '{attribute.split(".")[-1]}' called (value={value})")
            return value

        def setter(instance, value: Any) -> None:
            attr = instance
            for attr_name in attribute.split("."):
                attr = getattr(attr, attr_name)
            old_value = attr
            instance.logger.debug(f"Setter '{attribute.split(".")[-1]}' called (value={value})")

            if old_value == value:
                instance.logger.debug(f"Skipped '{attribute.split(".")[-1]}' update (same value)")
                return

            if custom_setter:
                if not custom_setter(instance, value):
                    return

            with instance.updating(attribute):
                attrs = attribute.split(".")
                attr = instance
                for attr_name in attrs[:-1]:
                    attr = getattr(attr, attr_name)
                setattr(attr, attrs[-1], value)
                instance.logger.debug(f"Emitting {notify_signal} after model update")
                getattr(instance, notify_signal).emit()

        return Property(property_type, getter, setter,
                        notify=lambda instance: getattr(instance, notify_signal))  # type: ignore[assignment]
