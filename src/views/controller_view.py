from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QVBoxLayout, QFrame

from app_domain.controlsys import AntiWindup
from viewmodels import LanguageViewModel, ControllerViewModel
from views import BaseView, FieldConfig
from .translations import Translation

FIELDS: list[FieldConfig] = [
    FieldConfig("controller_type", QLabel),
    FieldConfig("anti_windup", QComboBox),
]


class ControllerView(BaseView, QWidget):
    def __init__(self, vm_lang: LanguageViewModel, vm_controller: ControllerViewModel):
        QWidget.__init__(self)

        self._vm_controller = vm_controller

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = QVBoxLayout()

        main_layout.addWidget(self._create_controller_frame())

        self.setLayout(main_layout)

    def _create_controller_frame(self) -> QFrame:

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_controller = QLabel()
        self._apply_title_property(self._lbl_title_controller)
        frame_layout.addWidget(self._lbl_title_controller)
        frame_layout.addLayout(self._create_grid(FIELDS))

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        ...

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        ...

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_controller.setText(self.tr("Controller"))

        labels = {
            "controller_type": self.tr("Controller Type"),
            "anti_windup": self.tr("Anti Windup"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        translation = Translation()
        self._cmb_add_item(self._widgets["anti_windup"], translation(AntiWindup))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._widgets["controller_type"].setText(self._vm_controller.controller_type)

        index = self._widgets["anti_windup"].findData(self._vm_controller.anti_windup)
        if index >= 0:
            self._widgets["anti_windup"].setCurrentIndex(index)
