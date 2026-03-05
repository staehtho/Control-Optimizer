from PySide6.QtCore import QObject, QT_TRANSLATE_NOOP
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QSizePolicy
from numpy import ndarray

from app_domain.ui_context import UiContext
from app_domain.functions import FunctionTypes, resolve_function_type
from viewmodels import FunctionViewModel, PlotViewModel
from viewmodels.types import PlotData
from views import BaseView
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, FunctionWidget, ExpandableFrame
from views.translations import PlotLabels


class FunctionView(BaseView, QWidget):
    """View for selecting and configuring functions and displaying the plot."""

    def __init__(
            self,
            ui_context: UiContext,
            vm_function: FunctionViewModel,
            vm_plot: PlotViewModel,
            parent: QObject | None = None,
    ) -> None:
        QWidget.__init__(self, parent)

        self._vm_function = vm_function
        self._vm_plot = vm_plot

        self._txt_function_params: dict[str, QLineEdit] = {}

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title)

        self._frm_function = self._create_function_frame()
        main_layout.addWidget(self._frm_function, 0)
        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_function_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card()

        self._function_widget = FunctionWidget(
            self._ui_context, self._vm_function, [FunctionTypes.NULL], self
        )

        frame_layout.addWidget(self._function_widget)

        return frame

    def _create_plot_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(expand_vertically_when_expanded=True)

        function_type = resolve_function_type(self._vm_function.selected_function)
        title = self._enum_translation(FunctionTypes).get(function_type)
        self._plot_cfg = PlotWidgetConfiguration(
            context="ControlEnums",
            title=title,
            x_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Output")),
        )

        plot_view = PlotWidget(self._ui_context, self._vm_plot, self._plot_cfg, parent=self)
        plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        frame_layout.addWidget(plot_view, 1)

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._function_widget.functionChanged.connect(self._on_vm_function_changed)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""

        # Function ViewModel → View
        self._vm_function.computeFinished.connect(self._on_vm_compute_finished)

        # Plot ViewModel → Function recomputation
        self._vm_plot.xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Excitation Function"))
        self._frm_function.set_title(self.tr("Function"))
        self._frm_plot.set_title(self.tr("Function Plot"))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self._vm_function.compute_function(t0, t1)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_function_changed(self) -> None:
        """Rebuild parameter grid when selected function changes."""
        self._logger.info(f"Function changed to: {self._vm_function.selected_function.__class__.__name__}")

        function_type = resolve_function_type(self._vm_function.selected_function)
        self._plot_cfg.title = self._enum_translation(FunctionTypes).get(function_type)

        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self._vm_function.compute_function(t0, t1)

    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        """Update plot data after function computation completes."""
        self._logger.debug("Function computation finished, updating plot")
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.FUNCTION.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.FUNCTION),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.FUNCTION),
            )
        )

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max
        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._vm_function.compute_function(t0, t1)

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
