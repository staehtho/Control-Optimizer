from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QSizePolicy
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
    figsize: tuple[float, float]

class PlotView(BaseView, QWidget):
    def __init__(self, vm: PlotViewModel, plot_configuration: PlotConfiguration, vm_lang: LanguageViewModel, parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm = vm
        self._cfg = plot_configuration

        BaseView.__init__(self, vm_lang)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.addLayout(self._create_header())

        # figure
        self._figure = Figure(self._cfg.figsize)
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)    # type: ignore[attr-defined]
        main_layout.addWidget(self._toolbar)
        main_layout.addWidget(self._canvas)

        self.setLayout(main_layout)

    def _create_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        # Grid checkbox
        self._chk_grid = QCheckBox("")
        self._chk_grid.setChecked(self._vm.grid)
        layout.addWidget(self._chk_grid)

        # Start time
        self._lbl_start = QLabel("")
        layout.addWidget(self._lbl_start)

        self._txt_start = QLineEdit()
        self._txt_start.setText(f"{self._vm.start_time:.2f}")  # 2 decimal places
        self._txt_start.setValidator(QDoubleValidator())
        layout.addWidget(self._txt_start)

        # End time
        self._lbl_end = QLabel("")
        layout.addWidget(self._lbl_end)

        self._txt_end = QLineEdit()
        self._txt_end.setText(f"{self._vm.end_time:.2f}")  # 2 decimal places
        self._txt_end.setValidator(QDoubleValidator())
        layout.addWidget(self._txt_end)

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
        self._update_plot()

    # -------------------------------------------------
    # Plot update
    # -------------------------------------------------
    def _update_plot(self) -> None:
        """
        Redraw the plot safely, add legend if multiple series, set grid and limits.
        Thread-safe via QMetaObject.invokeMethod.
        """
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        data = self._vm.get_data()
        for label, series in data.items():
            ax.plot(*series, label=label)

        # Add legend only if multiple series
        if len(data) > 1:
            ax.legend()

        ax.set_title(QCoreApplication.translate(self._cfg.context, self._cfg.title))
        ax.set_xlabel(QCoreApplication.translate(self._cfg.context, self._cfg.x_label))
        ax.set_ylabel(QCoreApplication.translate(self._cfg.context, self._cfg.y_label))
        ax.grid(self._vm.grid)
        ax.set_xlim(self._vm.start_time, self._vm.end_time)

        self._figure.tight_layout()
        self._canvas.draw()

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_chk_grid_changed(self) -> None:
        self._vm.grid = self._chk_grid.isChecked()

    def _on_txt_start_changed(self):
        try:
            value = float(self._txt_start.text())
        except ValueError:
            self._txt_start.setText(f"{self._vm.start_time:.2f}")
            return
        self._vm.start_time = value
        self._txt_start.setText(f"{value:.2f}")  # format input

    def _on_txt_end_changed(self):
        try:
            value = float(self._txt_end.text())
        except ValueError:
            self._txt_end.setText(f"{self._vm.end_time:.2f}")
            return
        self._vm.end_time = value
        self._txt_end.setText(f"{value:.2f}")  # format input

    def resizeEvent(self, event):
        self._figure.tight_layout()
        self._canvas.draw()

        # Call the base class implementation (important!)
        super().resizeEvent(event)