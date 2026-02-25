from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QSizePolicy, QFrame
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QDoubleValidator
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from dataclasses import dataclass

from viewmodels import PlotViewModel, LanguageViewModel
from views import BaseView

@dataclass
class PlotConfiguration:
    context: str
    title: str
    x_label: str
    y_label: str

class PlotView(BaseView, QWidget):
    def __init__(self, vm: PlotViewModel, plot_configuration: PlotConfiguration, vm_lang: LanguageViewModel, parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm = vm
        self._cfg = plot_configuration

        BaseView.__init__(self, vm_lang)
        self._logger.debug("PlotView initialized (context=%s)", self._cfg.context)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel) # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised) # type: ignore[attr-defined]

        frame_layout = QVBoxLayout()
        frame_layout.addLayout(self._create_header())

        # figure
        self._figure = Figure(constrained_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)    # type: ignore[attr-defined]
        self._canvas.setMinimumSize(400, 250)
        self._update_plot()

        frame_layout.addWidget(self._toolbar)
        frame_layout.addWidget(self._canvas)

        frame.setLayout(frame_layout)
        main_layout.addWidget(frame)
        self.setLayout(main_layout)

    def _create_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        # Start time
        self._lbl_start = QLabel("")
        self._lbl_start.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed) # type: ignore[attr-defined]
        layout.addWidget(self._lbl_start)

        self._txt_start = QLineEdit()
        self._txt_start.setFixedWidth(90)
        self._txt_start.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed) # type: ignore[attr-defined]
        self._txt_start.setText(f"{self._vm.start_time:.{self._dec}f}")
        self._txt_start.setValidator(QDoubleValidator())
        layout.addWidget(self._txt_start)

        # End time
        self._lbl_end = QLabel("")
        self._lbl_end.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)   # type: ignore[attr-defined]
        layout.addWidget(self._lbl_end)

        self._txt_end = QLineEdit()
        self._txt_end.setFixedWidth(90)
        self._txt_end.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)   # type: ignore[attr-defined]
        self._txt_end.setText(f"{self._vm.end_time:.{self._dec}f}")
        self._txt_end.setValidator(QDoubleValidator())
        layout.addWidget(self._txt_end)

        # Grid checkbox
        self._chk_grid = QCheckBox("")
        self._chk_grid.setChecked(self._vm.grid)
        self._chk_grid.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        layout.addWidget(self._chk_grid)

        layout.addStretch()  # keeps everything left-aligned

        return layout

    # -------------------------------------------------
    # Signal connections (UI → ViewModel)
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        self._chk_grid.stateChanged.connect(self._on_chk_grid_changed)
        self._txt_start.editingFinished.connect(self._on_txt_start_changed)
        self._txt_start.returnPressed.connect(self._on_txt_start_changed)
        self._txt_end.editingFinished.connect(self._on_txt_end_changed)
        self._txt_end.returnPressed.connect(self._on_txt_end_changed)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        # Thread-safe call to update plot
        self._vm.gridChanged.connect(self._update_plot)
        self._vm.startTimeChanged.connect(self._update_plot)
        self._vm.endTimeChanged.connect(self._update_plot)
        self._vm.dataChanged.connect(self._update_plot)

    def _retranslate(self) -> None:
        self._chk_grid.setText(self.tr("plot.grid"))
        self._lbl_start.setText(self.tr("plot.start"))
        self._lbl_end.setText(self.tr("plot.end"))
        self._txt_start.setToolTip(self.tr("plot.start.tooltip"))
        self._txt_end.setToolTip(self.tr("plot.end.tooltip"))
        self._update_plot()

    # -------------------------------------------------
    # Plot update
    # -------------------------------------------------
    def _update_plot(self) -> None:
        """
        Redraw the plot safely, add legend if multiple series, set grid and limits.
        Thread-safe via QMetaObject.invokeMethod.
        """
        self._logger.debug(
            "Updating plot (grid=%s, xlim=[%f, %f])",
            self._vm.grid,
            self._vm.start_time,
            self._vm.end_time
        )
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        data = self._vm.get_data()
        self._logger.debug("Plot contains %d data series", len(data))

        for label, series in data.items():
            self._logger.debug("Plotting series: %s (points=%d)", label, len(series[0]))
            ax.plot(*series, label=label)

        # Add legend only if multiple series
        if len(data) > 1:
            ax.legend()

        ax.set_title(QCoreApplication.translate(self._cfg.context, self._cfg.title))
        ax.set_xlabel(QCoreApplication.translate(self._cfg.context, self._cfg.x_label))
        ax.set_ylabel(QCoreApplication.translate(self._cfg.context, self._cfg.y_label))
        ax.grid(self._vm.grid)
        ax.set_xlim(self._vm.start_time, self._vm.end_time)

        self._canvas.draw()

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_chk_grid_changed(self) -> None:
        checked = self._chk_grid.isChecked()
        self._logger.debug("UI event: grid changed -> %s", checked)
        self._vm.grid = checked

    def _on_txt_start_changed(self):
        try:
            value = float(self._txt_start.text())
        except ValueError:
            self._logger.warning("Invalid start time input: %s", self._txt_start.text())
            self._txt_start.setText(f"{self._vm.start_time:.{self._dec}f}")
            return

        self._logger.debug("UI event: start_time changed -> %f", value)
        self._vm.start_time = value
        self._txt_start.setText(f"{value:.{self._dec}f}")

    def _on_txt_end_changed(self):
        try:
            value = float(self._txt_end.text())
        except ValueError:
            self._logger.warning("Invalid end time input: %s", self._txt_end.text())
            self._txt_end.setText(f"{self._vm.end_time:.{self._dec}f}")
            return

        self._logger.debug("UI event: end_time changed -> %f", value)
        self._vm.end_time = value
        self._txt_end.setText(f"{value:.{self._dec}f}")

    def resizeEvent(self, event):
        self._canvas.draw_idle()
        super().resizeEvent(event)