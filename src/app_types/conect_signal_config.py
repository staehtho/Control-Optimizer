from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING, Protocol, Callable
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

    from .field import FieldType

type SimpleHandler = Callable[..., None]


class EventHandler(Protocol):
    """Protocol for the main event handler."""

    def __call__(
            self,
            view: Any,
            widget: QObject,
            key: str | FieldType,
            attr_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        ...


@dataclass
class ConnectSignalConfig:
    """Configuration for connecting a Qt signal to a handler pipeline.

    This configuration object defines how a signal emitted by a QObject
    (e.g., QWidget or ViewModel) is processed. It supports four levels
    of handling:

    1. Override handler:
        If provided, this handler replaces all other logic.
    2. Pre-handler:
        If provided, this handler is executed before the main handler.
    3. Main handler:
        The default handler responsible for processing the signal
        (e.g., syncing UI ↔ ViewModel).
    4. Post-handler:
        If provided, this handler is executed after the main handler.

    Attributes:
        key (str | FieldType):
            Identifier for the field associated with the signal.
        signal_name (str):
            Name of the Qt signal to connect (e.g., "editingFinished").
        attr_name (str):
            Target attribute name (typically in the ViewModel).
        widget (QObject):
            The object emitting the signal (QWidget or ViewModel).
        kwargs (dict[str, Any]):
            Additional keyword arguments passed to handlers.
        main_event_handler (Optional[EventHandler]):
            The main handler executed after the pre-handler.
        pre_event_handler (Optional[SimpleHandler]):
            Optional handler executed before the main handler.
        post_event_handler (Optional[SimpleHandler]):
            Optional handler executed after the main handler.
        override_event_handler (Optional[SimpleHandler]):
            Optional handler that replaces all other handlers.
    """

    key: str | FieldType
    signal_name: str
    attr_name: str
    widget: QObject
    kwargs: dict[str, Any] = field(default_factory=dict)

    # Main handler (widget OR VM)
    main_event_handler: Optional[EventHandler] = None

    # Runs BEFORE main handler
    pre_event_handler: Optional[SimpleHandler] = None

    # Runs AFTER main handler
    post_event_handler: Optional[SimpleHandler] = None

    # Replaces everything
    override_event_handler: Optional[SimpleHandler] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            AttributeError: If the widget does not have the specified signal.
            ValueError: If both custom and override handlers are provided.
        """
        if not hasattr(self.widget, self.signal_name):
            raise AttributeError(
                f"{self.widget} has no signal {self.signal_name}"
            )

        if self.override_event_handler and (
                self.pre_event_handler or self.post_event_handler or self.main_event_handler):
            raise ValueError(
                "override_event_handler cannot be combined with other handlers."
            )
