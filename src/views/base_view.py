import logging
from PySide6.QtWidgets import QLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from viewmodels import LanguageViewModel

class BaseView:
    """
    Base class for all Views in the application.

    Responsibilities:
    - Bind to LanguageViewModel for UI translations
    - Provide a logger for debugging
    - Structured lifecycle: UI creation, signals, ViewModel bindings
    - Abstract methods enforce that concrete Views implement required functionality
    """

    def __init__(self, vm_lang: LanguageViewModel):

        # -----------------------------
        # Language support
        # -----------------------------
        # Store reference to the LanguageViewModel
        self._vm_lang = vm_lang
        # Connect signal: whenever language changes, call _retranslate
        self._vm_lang.languageChanged.connect(self._retranslate)

        # Scale factor for rendering the LaTeX formula
        self._formula_font_size_scale = 1.5
        self._dec = 3
        self._title_size = 16

        # -----------------------------
        # Logging setup
        # -----------------------------
        self._logger = logging.getLogger(f"View.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(f"{self.__class__.__name__} initialized")

        # -----------------------------
        # View lifecycle
        # -----------------------------
        # Step 1: Initialize UI components (widgets, layouts, etc.)
        self._init_ui()
        self._logger.debug("UI initialized")

        # Step 2: Connect UI signals (buttons, inputs, etc.)
        self._connect_signals()
        self._logger.debug("UI signals connected")

        # Step 3: Bind ViewModel signals to the View
        self._bind_vm()
        self._logger.debug("ViewModel bindings set up")

        # Step 4: Initial translation
        # Call _retranslate explicitly because the signal only fires on changes,
        # ensuring UI shows the correct initial language
        self._retranslate()
        self._logger.debug("initial translation applied")

    # ---------- Lifecycle abstract methods ----------

    def _init_ui(self) -> None:
        """Create and configure UI elements (widgets, layouts, etc.)."""
        raise NotImplementedError

    def _connect_signals(self) -> None:
        """Connect UI signals (buttons, input fields, etc.) to handlers."""
        raise NotImplementedError

    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View updates (model → view)."""
        raise NotImplementedError

    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        raise NotImplementedError

    def _clear_layout(self, layout: QLayout) -> None:
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def _apply_title_property(self, lbl: QLabel, font_size: int = 0) -> None:
        font = QFont()
        font.setPointSize(self._title_size if font_size == 0 else font_size)  # size in pt
        font.setBold(True)
        lbl.setFont(font)
        lbl.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]
