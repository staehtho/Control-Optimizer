from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QT_TRANSLATE_NOOP
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QSizePolicy, QHBoxLayout
from numpy import ndarray

from app_domain.functions import FunctionTypes, resolve_function_type
from app_types import PlotData, PlotLabels
from views import ViewMixin
from views.plot_style import PLOT_STYLE
from resources.resources import Icons
from views.widgets import PlotWidget, PlotWidgetConfiguration, FunctionWidget

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import FunctionViewModel, PlotViewModel
    from views.widgets import SectionFrame


class FunctionView(ViewMixin, QWidget):
    """View for selecting and configuring functions and displaying the plot."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
            self,
            ui_context: UiContext,
            vm_function: FunctionViewModel,
            vm_plot: PlotViewModel,
            parent: QWidget | None = None,
    ) -> None:
        QWidget.__init__(self, parent)

        self._vm_function = vm_function
        self._vm_plot = vm_plot

        self._txt_function_params: dict[str, QLineEdit] = {}

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.excitation_function, self._title_icon_size)
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

        self._frm_function = self._create_function_frame()
        main_layout.addWidget(self._frm_function, 0)
        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        main_layout.addLayout(self._create_navigation_buttons_layout(parent=self))
        self.setLayout(main_layout)

    def _create_function_frame(self) -> SectionFrame:
        """Create the function configuration card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        excluded_function_types: list[FunctionTypes] = [
            FunctionTypes.NULL,
            FunctionTypes.BROWNIAN_NOISE,
            FunctionTypes.PINK_NOISE,
            FunctionTypes.WHITE_NOISE
        ]

        self._function_widget = FunctionWidget(
            self._ui_context, self._vm_function, excluded_function_types, parent=self
        )

        frame_layout.addWidget(self._function_widget)

        return frame

    def _create_plot_frame(self) -> SectionFrame:
        """Create the function plot card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        self._plot_cfg = PlotWidgetConfiguration(
            context="FunctionView",
            x_label=str(QT_TRANSLATE_NOOP("FunctionView", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("FunctionView", "Output")),
        )

        plot_view = PlotWidget(self._ui_context, self._vm_plot, self._plot_cfg, parent=self)
        plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        frame_layout.addWidget(plot_view, 1)

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._function_widget.functionChanged.connect(self._on_vm_function_changed)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""

        # Function ViewModel -> View
        self._vm_function.computeFinished.connect(self._on_vm_compute_finished)

        # Plot ViewModel -> Function recomputation
        self._vm_plot.xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_vm_time_changed)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self.tr("Excitation Function"))
        self._frm_function.setText(self.tr("Excitation Function Definition"))
        self._frm_plot.setText(self.tr("Excitation Function Plot"))

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self._vm_function.compute_function(t0, t1)

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.excitation_function, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_function_changed(self) -> None:
        """Rebuild parameter grid when selected function changes."""
        self.logger.info(f"Function changed to: {self._vm_function.selected_function.__class__.__name__}")

        function_type = resolve_function_type(self._vm_function.selected_function)
        self._plot_cfg.title = self._enum_translation(function_type)

        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self._vm_function.compute_function(t0, t1)

    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        """Update plot data after function computation completes."""
        self.logger.debug("Function computation finished, updating plot")
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.FUNCTION.value,
                label=self._enum_translation(PlotLabels.FUNCTION),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.FUNCTION),
            )
        )

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self.logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._vm_function.compute_function(t0, t1)
