from __future__ import annotations
from typing import TYPE_CHECKING, Any
from functools import partial

from PySide6.QtCore import QRegularExpression, Qt, QT_TRANSLATE_NOOP
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QHBoxLayout, QTabWidget
from typing import Callable
from numpy import ndarray

from app_types import PlotData, PlantField, PlotLabels, ConnectSignalConfig
from views import ViewMixin
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, FormulaWidget
from resources.resources import Icons

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from app_types import PlotField
    from viewmodels import PlantViewModel, PlotViewModel
    from views.widgets import SectionFrame


TXT_WIDTH = 220

class PlantView(ViewMixin, QWidget):
    """Plant view for editing a transfer function and showing its step response."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
        self,
            ui_context: UiContext,
        vm_plant: PlantViewModel,
        vm_plot: PlotViewModel,
            parent: QWidget = None,
    ):
        QWidget.__init__(self, parent)

        # Reference to the ViewModel
        self._vm_plant = vm_plant
        self._vm_plot = vm_plot

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.plant, self._title_icon_size)
        self._label_icon = QLabel(self)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))
        self._label_icon.setFixedSize(self._title_icon_size, self._title_icon_size)

        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        title_layout.addWidget(self._label_icon)
        title_layout.addWidget(self._lbl_title)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        self._frm_tf = self._create_transfer_function_frame()
        main_layout.addWidget(self._frm_tf, 0)
        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        main_layout.addLayout(self._create_navigation_buttons_layout(pre_btn=False, parent=self))
        self.setLayout(main_layout)

    def _create_transfer_function_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        self._tf_tab = QTabWidget(frame)
        frame_layout.addWidget(self._tf_tab)

        widget_polynom = self._create_polynom_widget()
        self._tf_tab.addTab(widget_polynom, "")

        widget_binominal = self._create_binominal_widget()
        self._tf_tab.addTab(widget_binominal, "")

        return frame

    def _create_polynom_widget(self) -> QWidget:
        """Create the polynom widget to define the transfer function with polynom."""
        widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setColumnMinimumWidth(0, 100)

        # Validator: allow only digits, dot, comma, minus and whitespace
        regex = QRegularExpression(r"[0-9.,\-\s]*")
        validator = QRegularExpressionValidator(regex)

        # -------------------
        # Numerator input
        # -------------------
        lbl_num = QLabel(widget)

        txt_num = QLineEdit(widget)
        txt_num.setValidator(validator)

        # Set fixed width (height follows style automatically)
        txt_num.setFixedWidth(TXT_WIDTH)

        grid_layout.addWidget(lbl_num, 0, 0)
        grid_layout.addWidget(txt_num, 0, 1)

        self.labels.setdefault(PlantField.NUM, lbl_num)
        self.field_widgets.setdefault(PlantField.NUM, txt_num)

        # -------------------
        # Denominator input
        # -------------------
        lbl_den = QLabel(widget)

        txt_den = QLineEdit(widget)
        txt_den.setValidator(validator)

        # Same fixed width for visual consistency
        txt_den.setFixedWidth(TXT_WIDTH)

        grid_layout.addWidget(lbl_den, 1, 0)
        grid_layout.addWidget(txt_den, 1, 1)

        self.labels.setdefault(PlantField.DEN, lbl_den)
        self.field_widgets.setdefault(PlantField.DEN, txt_den)

        # -------------------
        # Transfer function formula display
        # -------------------
        formula = FormulaWidget(font_size_scale=self._formula_font_size_scale, parent=widget)
        self.field_widgets.setdefault(PlantField.POLYNOM_FORMULA, formula)

        # --- Scroll area for label ---
        scroll_formula = QScrollArea(widget)
        scroll_formula.setWidget(formula)
        scroll_formula.setWidgetResizable(True)
        scroll_formula.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_formula.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_formula.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_formula.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # cannot be focused at all
        scroll_formula.setStyleSheet("background: transparent;")
        scroll_formula.viewport().setStyleSheet("background: transparent;")

        grid_layout.addWidget(scroll_formula, 0, 2, 4, 1)

        widget.setLayout(grid_layout)

        return widget

    def _create_binominal_widget(self) -> QWidget:
        """Create the binominal widget to define the transfer function with zeros and poles"""
        widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setColumnMinimumWidth(0, 100)

        # Validator: allow only digits, dot, comma, minus and whitespace
        regex = QRegularExpression(r"[s*^0-9.\-\s\(\)+]*")
        validator = QRegularExpressionValidator(regex)

        # -------------------
        # Zero input
        # -------------------
        lbl_zero = QLabel(widget)

        txt_zero = QLineEdit(widget)
        txt_zero.setValidator(validator)

        # Set fixed width (height follows style automatically)
        txt_zero.setFixedWidth(TXT_WIDTH)

        grid_layout.addWidget(lbl_zero, 0, 0)
        grid_layout.addWidget(txt_zero, 0, 1)

        self.labels.setdefault(PlantField.ZERO, lbl_zero)
        self.field_widgets.setdefault(PlantField.ZERO, txt_zero)

        # -------------------
        # Pole input
        # -------------------
        lbl_pole = QLabel(widget)

        txt_pole = QLineEdit(widget)
        txt_pole.setValidator(validator)

        # Set fixed width (height follows style automatically)
        txt_pole.setFixedWidth(TXT_WIDTH)

        grid_layout.addWidget(lbl_pole, 1, 0)
        grid_layout.addWidget(txt_pole, 1, 1)

        self.labels.setdefault(PlantField.POLE, lbl_pole)
        self.field_widgets.setdefault(PlantField.POLE, txt_pole)

        # -------------------
        # Transfer function formula display
        # -------------------
        formula = FormulaWidget(font_size_scale=self._formula_font_size_scale, parent=widget)
        self.field_widgets.setdefault(PlantField.BINOMINAL_FORMULA, formula)

        # --- Scroll area for label ---
        scroll_formula = QScrollArea(widget)
        scroll_formula.setWidget(formula)
        scroll_formula.setWidgetResizable(True)
        scroll_formula.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_formula.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_formula.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_formula.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # cannot be focused at all
        scroll_formula.setStyleSheet("background: transparent;")
        scroll_formula.viewport().setStyleSheet("background: transparent;")

        grid_layout.addWidget(scroll_formula, 0, 2, 4, 1)

        widget.setLayout(grid_layout)

        return widget

    def _create_plot_frame(self) -> SectionFrame:
        """Create the step response plot card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)
        plot_cfg = PlotWidgetConfiguration(
            context="PlantView",
            title=str(QT_TRANSLATE_NOOP("PlantView", "Step Response")),
            x_label=str(QT_TRANSLATE_NOOP("PlantView", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("PlantView", "Output")),
            show_x_min=False
        )

        plot_view = PlotWidget(self._ui_context, self._vm_plot, plot_cfg, parent=self)
        plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        frame_layout.addWidget(plot_view, 1)

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._tf_tab.currentChanged.connect(self._vm_plant.update_tf_tab)

        self._connect_object_signals(self._get_widget_bindings())

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm plant
        self._vm_plant.validationFailed.connect(self._on_validation_failed)
        self._vm_plant.polyTfChanged.connect(self._on_vm_formula_changed)
        self._vm_plant.stepResponseChanged.connect(self._on_step_response_changed)
        # vm plot
        self._vm_plot.xMinChanged.connect(self._on_plot_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_plot_time_changed)

        self._connect_object_signals(self._get_vm_bindings())

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self.tr("Plant"))
        self._frm_tf.setText(self.tr("Transfer function"))
        self._frm_plot.setText(self.tr("Step Response"))

        # translate pages
        self._tf_tab.setTabText(0, self.tr("Polynomial"))
        self._tf_tab.setTabText(1, self.tr("Pole-Zeros"))

        self.labels.get(PlantField.NUM).setText(self.tr("plant.num"))
        self.labels.get(PlantField.DEN).setText(self.tr("plant.den"))
        self.labels.get(PlantField.ZERO).setText(self.tr("plant.zero"))
        self.labels.get(PlantField.POLE).setText(self.tr("plant.pole"))

        self.field_widgets.get(PlantField.NUM).setPlaceholderText(self.tr("e.g. 1  → 1"))
        self.field_widgets.get(PlantField.DEN).setPlaceholderText(self.tr("e.g. 1, 2, 1  → 1s² + 2s + 1"))
        self.field_widgets.get(PlantField.ZERO).setPlaceholderText(self.tr("e.g. 1  → 1"))
        self.field_widgets.get(PlantField.POLE).setPlaceholderText(self.tr("e.g. (s + 1)^2  → (s + 1)²"))

        tooltip_text_nd = self.tr("""Enter coefficients separated by commas, spaces, or semicolons.
        Use '.' as the decimal point.
        The first number corresponds to the highest power of s.
        Example: 1, 0.5, 2 → 1*s² + 0.5*s + 2""")
        self.field_widgets.get(PlantField.NUM).setToolTip(tooltip_text_nd)
        self.field_widgets.get(PlantField.DEN).setToolTip(tooltip_text_nd)

        tooltip_text_zp = self.tr("""Enter a polynomial expression in s (factors or expanded form).
        Use parentheses for factors. Multiplication can be implicit.
        Use '^' for powers.
        Example: (s+1)(s+2) or s^2 + 3*s + 2""")
        self.field_widgets.get(PlantField.ZERO).setToolTip(tooltip_text_zp)
        self.field_widgets.get(PlantField.POLE).setToolTip(tooltip_text_zp)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._set_formula()
        self._vm_plant.update_tf_tab(self._tf_tab.currentIndex())

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.plant, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

        self._set_formula()

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_formula_changed(self) -> None:
        """Update LaTeX formula label when ViewModel formula changes."""
        self._set_formula()

    def _on_plot_time_changed(self) -> None:
        """Update plot when start or end time changes."""
        self._vm_plant.compute_step_response(self._vm_plot.x_min, self._vm_plot.x_max)

    def _on_step_response_changed(self, t: ndarray, y: ndarray) -> None:
        """Update plot series when the step response changes."""
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.PLANT.value,
                label=self._enum_translation(PlotLabels.PLANT),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
            )
        )

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_txt_changed(self, value: str, **kwargs: Any) -> None:
        """Handle user changes in QLineEdit field."""
        field = kwargs.get("field")
        if not isinstance(field, QLineEdit) or field is None:
            raise TypeError(f"Expected QObject, got {type(field)}")

        setter = kwargs.get("setter")
        if not isinstance(setter, Callable) or setter is None:
            raise TypeError(f"Expected Callable, got {type(setter)}")

        self._clear_input_error(field)
        self.logger.debug(f"UI event: txt_change changed (value={value})")
        setter(value)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _set_formula(self) -> None:
        """Update the LaTeX formula display from the ViewModel transfer function."""
        self.field_widgets.get(PlantField.POLYNOM_FORMULA).set_formula(r"G(s) = " + self._vm_plant.get_poly_tf())
        self.field_widgets.get(PlantField.BINOMINAL_FORMULA).set_formula(r"G(s) = " + self._vm_plant.get_binom_tf())

    def _get_widget_bindings(self) -> list[ConnectSignalConfig]:
        k_num = PlantField.NUM
        k_den = PlantField.DEN
        k_zero = PlantField.ZERO
        k_pole = PlantField.POLE

        return [
            ConnectSignalConfig(
                key=k_num,
                signal_name="textChanged",
                attr_name="",
                widget=self.field_widgets[k_num],
                kwargs={
                    "field": self.field_widgets[k_num],
                    "setter": lambda value: self._vm_plant.update_num(value)
                },
                override_event_handler=self._on_txt_changed
            ),
            ConnectSignalConfig(
                key=k_den,
                signal_name="textChanged",
                attr_name="",
                widget=self.field_widgets[k_den],
                kwargs={
                    "field": self.field_widgets[k_den],
                    "setter": lambda value: self._vm_plant.update_den(value)
                },
                override_event_handler=self._on_txt_changed
            ),
            ConnectSignalConfig(
                key=k_zero,
                signal_name="textChanged",
                attr_name="",
                widget=self.field_widgets[k_zero],
                kwargs={
                    "field": self.field_widgets[k_zero],
                    "setter": lambda value: self._vm_plant.update_zero(value)
                },
                override_event_handler=self._on_txt_changed
            ),
            ConnectSignalConfig(
                key=k_pole,
                signal_name="textChanged",
                attr_name="",
                widget=self.field_widgets[k_pole],
                kwargs={
                    "field": self.field_widgets[k_pole],
                    "setter": lambda value: self._vm_plant.update_pole(value)
                },
                override_event_handler=self._on_txt_changed
            ),
        ]

    def _get_vm_bindings(self) -> list[ConnectSignalConfig]:
        k_num = PlantField.NUM
        k_den = PlantField.DEN
        k_zero = PlantField.ZERO
        k_pole = PlantField.POLE

        return [
            ConnectSignalConfig(
                key=k_num,
                signal_name="numChanged",
                attr_name="num",
                widget=self._vm_plant,
                kwargs={"field": self.field_widgets.get(k_num)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_den,
                signal_name="denChanged",
                attr_name="den",
                widget=self._vm_plant,
                kwargs={"field": self.field_widgets.get(k_den)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_zero,
                signal_name="zeroChanged",
                attr_name="zero",
                widget=self._vm_plant,
                kwargs={"field": self.field_widgets.get(k_zero)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_pole,
                signal_name="poleChanged",
                attr_name="pole",
                widget=self._vm_plant,
                kwargs={"field": self.field_widgets.get(k_pole)},
                main_event_handler=self._on_vm_changed
            ),
        ]
