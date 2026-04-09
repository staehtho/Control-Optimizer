from contextlib import contextmanager
import logging
from typing import Iterator

from PySide6.QtCore import QObject, Signal, Slot

from app_types import ValidationResult, FieldType


class BaseViewModel(QObject):
    """
    Base class for all ViewModels.

    Provides common infrastructure for:
    - preventing feedback loops between UI and model updates
    - centralized validation error reporting
    - consistent logging

    The class implements an **update guard mechanism** using a context manager.
    When a field is updated programmatically, it can be temporarily marked as
    "updating" to prevent signals from triggering recursive updates.

    Subclasses should implement `_connect_signals()` to wire model signals
    to ViewModel properties.
    """

    #: Emitted when validation of a property fails.
    #: Contains the field identifier and the validation error message.
    validationFailed = Signal(FieldType, str)
    saveSvgRequested = Signal(object)
    svgExportFinished = Signal()

    def __init__(self, parent: QObject = None):
        """
        Initialize the base ViewModel.

        Args:
            parent: Optional Qt parent object.
        """
        super().__init__(parent)

        # Tracks fields that are currently being updated to avoid feedback loops.
        self._updating_fields: set[str] = set()

        # Dedicated logger per ViewModel instance.
        self.logger = logging.getLogger(f"ViewModel.{self.__class__.__name__}")

    def _connect_signals(self) -> None:
        """
        Connect model signals to ViewModel slots.

        Subclasses must implement this method to establish the required
        signal connections between the underlying model and the ViewModel.
        """
        raise NotImplementedError

    def refresh_from_model(self) -> None:
        """Re-emit externally visible state after the underlying model changed."""
        return

    @contextmanager
    def updating(self, field: str) -> Iterator[None]:
        """
        Context manager that temporarily marks a field as updating.

        This is used to prevent **feedback loops** when updating properties
        programmatically that would otherwise trigger UI-bound signals.

        Example:
            with self.updating("kp_min"):
                self.kp_min = new_value

        Args:
            field: Name of the field currently being updated.
        """
        self._updating_fields.add(field)
        try:
            yield
        finally:
            self._updating_fields.discard(field)

    def check_update_allowed(self, field: str) -> bool:
        """
        Check whether updates for a field are currently allowed.

        Returns False if the field is marked as updating, which indicates
        that the update originated internally and should not trigger
        additional processing.

        Args:
            field: Field identifier.

        Returns:
            True if updates are allowed, False otherwise.
        """
        return field not in self._updating_fields

    @staticmethod
    def _validate_relation(*, value: float, other: float, relation: str, message: str) -> ValidationResult:
        """
        Validate a numeric relation between two values.

        This helper is used to implement consistent validation logic for
        properties that depend on a relational constraint (e.g. min/max).

        Supported relations:
        - "<"
        - ">"
        - "<="
        - ">="

        Args:
            value: The value being validated.
            other: The reference value used for comparison.
            relation: The relational operator to apply.
            message: Error message returned if validation fails.

        Returns:
            ValidationResult indicating whether the constraint is satisfied.
        """

        if relation == "<":
            valid = value < other
        elif relation == ">":
            valid = value > other
        elif relation == "<=":
            valid = value <= other
        elif relation == ">=":
            valid = value >= other
        else:
            raise NotImplementedError(f"Relation '{relation}' is not supported.")

        if not valid:
            return ValidationResult(False, message)

        return ValidationResult(True)

    def _verify(self, field: FieldType, result: ValidationResult) -> bool:
        """
        Process a validation result.

        If validation fails:
        - a warning is logged
        - the `validationFailed` signal is emitted

        Args:
            field: Identifier of the field that failed validation.
            result: Validation result.

        Returns:
            True if validation succeeded, otherwise False.
        """
        if not result.valid:
            self.logger.warning(result.message)
            self.validationFailed.emit(field, result.message)
            return False

        return True

    @Slot(object)
    def request_save_svg(self, request: dict[str, str]) -> None:
        self.logger.debug("Save SVG requested -> %s", request)
        self.saveSvgRequested.emit(request)

    @Slot()
    def notify_svg_export_finished(self) -> None:
        self.logger.debug("SVG export finished")
        self.svgExportFinished.emit()
