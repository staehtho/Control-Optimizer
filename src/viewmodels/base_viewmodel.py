from contextlib import contextmanager
import logging
from typing import Any, Callable, Iterator, Optional

from PySide6.QtCore import QObject, Property


class BaseViewModel(QObject):
    """Base ViewModel with an update-guard to avoid feedback loops."""

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

    @staticmethod
    def _logged_property(
            attribute: str,
            property_type: Any,
            read_only: bool = False,
            notify_signal: Optional[str] = None,
            custom_setter: Optional[Callable[..., Any]] = None,
    ) -> Property:
        field_name = attribute.split(".")[-1]

        def getter(instance) -> Any:
            attr = instance
            for attr_name in attribute.split("."):
                attr = getattr(attr, attr_name)
            value = attr
            instance.logger.debug(f"Getter '{field_name}' called (value={value})")
            return value

        def setter(instance, value: Any) -> None:
            attr = instance
            for attr_name in attribute.split("."):
                attr = getattr(attr, attr_name)
            old_value = attr
            instance.logger.debug(f"Setter '{field_name}' called (value={value})")

            if old_value == value:
                instance.logger.debug(f"Skipped '{field_name}' update (same value)")
                return

            if custom_setter:
                result = custom_setter(instance, value)

                # Legacy behavior: custom setter returns bool (allow/deny).
                if isinstance(result, bool):
                    if not result:
                        return
                # New behavior: custom setter returns transformed value or None (deny).
                elif result is None:
                    return
                else:
                    value = result

            with instance.updating(attribute):
                attrs = attribute.split(".")
                owner = instance
                for attr_name in attrs[:-1]:
                    owner = getattr(owner, attr_name)
                setattr(owner, attrs[-1], value)
                instance.logger.debug(f"Emitting {notify_signal} after model update")
                getattr(instance, notify_signal).emit()

        def notify(instance) -> None:
            if not read_only:
                getattr(instance, notify_signal)

        return Property(
            property_type,
            getter,
            None if read_only else setter,
            notify=None if read_only else notify
        )
