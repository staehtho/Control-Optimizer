from PySide6.QtCore import Property
from typing import Callable, Any, Optional


class LoggedProperty:
    def __init__(
            self,
            path: str,
            typ: Any,
            signal: Optional[str] = None,
            read_only: bool = False,
            custom_setter: Optional[Callable[..., Any]] = None
    ):

        self.path = path.split(".")
        self.typ = typ
        self.signal = signal
        self.read_only = read_only
        self.custom_setter = custom_setter

    def _resolve(self, instance):
        obj = instance
        for name in self.path[:-1]:
            obj = getattr(obj, name)
        return obj, self.path[-1]

    def getter(self, instance):
        obj = instance
        for name in self.path:
            obj = getattr(obj, name)

        instance.logger.debug(f"Getter '{self.path[-1]}' called (value={obj})")
        return obj

    def setter(self, instance, value):
        obj, field = self._resolve(instance)
        old_value = getattr(obj, field)

        instance.logger.debug(f"Setter '{field}' called (value={value})")

        if self.custom_setter:
            # always run validation
            valid_or_value = self.custom_setter(instance, value)
            if isinstance(valid_or_value, bool):
                if not valid_or_value:
                    return
            elif valid_or_value is None:
                return
            else:
                value = valid_or_value

        # Only update if the value changed
        if old_value != value:
            with instance.updating(".".join(self.path)):
                setattr(obj, field, value)

        # Emit signal always
        if self.signal:
            instance.logger.debug(f"Emitting {self.signal}")
            getattr(instance, self.signal).emit()

    def create_qt_property(self):
        return Property(
            self.typ,
            self.getter,
            None if self.read_only else self.setter,
            notify=None if not self.signal or self.read_only else getattr(self.owner, self.signal),
        )

    def __set_name__(self, owner, name):
        self.owner = owner
        setattr(owner, name, self.create_qt_property())
