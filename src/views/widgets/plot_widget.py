from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QSizePolicy
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QDoubleValidator, QColor, QPainter, QPixmap, QIcon
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib import cbook
from dataclasses import dataclass

from app_domain.ui_context import UiContext
from viewmodels import PlotViewModel
from views import BaseView


@dataclass
class PlotConfiguration:
    context: str
    title: str
    x_label: str
    y_label: str
    show_start_end_time: bool = True


class PlotWidget(BaseView, QWidget):
    def __init__(self, ui_context: UiContext, vm: PlotViewModel, plot_configuration: PlotConfiguration,
                 parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm = vm
        self._cfg = plot_configuration

        BaseView.__init__(self, ui_context)
        self._logger.debug(f"PlotWidget initialized (context={self._cfg.context})")

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        frame, frame_layout = self._create_card()
        frame_layout.addLayout(self._create_header())

        # figure
        self._figure = Figure()
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore[attr-defined]
        self._canvas.setMinimumSize(400, 250)
        self._apply_toolbar_icons()
        self._update_plot()

        frame_layout.addWidget(self._toolbar)
        frame_layout.addWidget(self._canvas)

        main_layout.addWidget(frame)
        self.setLayout(main_layout)

    def _create_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        show = self._cfg.show_start_end_time  # True = show, False = hide

        # Start time
        self._lbl_start = QLabel("")
        self._lbl_start.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        self._lbl_start.setVisible(show)
        layout.addWidget(self._lbl_start)

        self._txt_start = QLineEdit()
        self._txt_start.setFixedWidth(90)
        self._txt_start.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        self._txt_start.setValidator(QDoubleValidator())
        self._txt_start.setVisible(show)
        layout.addWidget(self._txt_start)

        # End time
        self._lbl_end = QLabel("")
        self._lbl_end.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        self._lbl_end.setVisible(show)
        layout.addWidget(self._lbl_end)

        self._txt_end = QLineEdit()
        self._txt_end.setFixedWidth(90)
        self._txt_end.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        self._txt_end.setValidator(QDoubleValidator())
        self._txt_end.setVisible(show)
        layout.addWidget(self._txt_end)

        # Grid checkbox
        self._chk_grid = QCheckBox("")
        self._chk_grid.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # type: ignore[attr-defined]
        layout.addWidget(self._chk_grid)

        layout.addStretch()  # keeps everything left-aligned

        return layout

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._chk_grid.stateChanged.connect(self._on_chk_grid_changed)
        self._txt_start.editingFinished.connect(self._on_txt_start_changed)
        self._txt_start.returnPressed.connect(self._on_txt_start_changed)
        self._txt_end.editingFinished.connect(self._on_txt_end_changed)
        self._txt_end.returnPressed.connect(self._on_txt_end_changed)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # Thread-safe call to update plot
        self._vm.gridChanged.connect(self._update_plot)
        self._vm.startTimeChanged.connect(self._update_plot)
        self._vm.endTimeChanged.connect(self._update_plot)
        self._vm.dataChanged.connect(self._update_plot)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._chk_grid.setText(self.tr("plot.grid"))
        self._lbl_start.setText(self.tr("plot.start"))
        self._lbl_end.setText(self.tr("plot.end"))
        self._txt_start.setToolTip(self.tr("plot.start.tooltip"))
        self._txt_end.setToolTip(self.tr("plot.end.tooltip"))
        self._update_plot()

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._txt_start.setText(f"{self._vm.start_time:.{self._dec}f}")
        self._txt_end.setText(f"{self._vm.end_time:.{self._dec}f}")
        self._chk_grid.setChecked(self._vm.grid)

    # -------------------------------------------------
    # Plot update
    # -------------------------------------------------
    def _update_plot(self) -> None:
        """
        Redraw the plot safely, add legend if multiple series, set grid and limits.
        Thread-safe via QMetaObject.invokeMethod.
        """
        self._logger.debug(
            f"Updating plot (grid={self._vm.grid}, xlim=[{self._vm.start_time:.6f}, {self._vm.end_time:.6f}])"
        )
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        data = self._vm.get_data()
        self._logger.debug(f"Plot contains {len(data)} data series")

        for label, series in data.items():
            self._logger.debug(f"Plotting series: {label} (points={len(series[0])})")
            ax.plot(*series, label=label)

        # Add legend only if multiple series
        if len(data) > 1:
            ax.legend()

        ax.set_title(QCoreApplication.translate(self._cfg.context, self._cfg.title))
        ax.set_xlabel(QCoreApplication.translate(self._cfg.context, self._cfg.x_label))
        ax.set_ylabel(QCoreApplication.translate(self._cfg.context, self._cfg.y_label))
        ax.grid(self._vm.grid)
        ax.set_xlim(self._vm.start_time, self._vm.end_time)

        start_text = f"{self._vm.start_time:.{self._dec}f}"
        end_text = f"{self._vm.end_time:.{self._dec}f}"
        if self._txt_start.text() != start_text:
            self._txt_start.setText(start_text)
        if self._txt_end.text() != end_text:
            self._txt_end.setText(end_text)

        self._canvas.draw()

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_chk_grid_changed(self) -> None:
        checked = self._chk_grid.isChecked()
        self._logger.debug(f"UI event: grid changed -> {checked}")
        self._vm.grid = checked

    def _on_txt_start_changed(self) -> None:
        try:
            value = float(self._txt_start.text())
        except ValueError:
            self._logger.warning(f"Invalid start time input: {self._txt_start.text()}")
            self._txt_start.setText(f"{self._vm.start_time:.{self._dec}f}")
            return

        self._logger.debug(f"UI event: start_time changed -> {value:.6f}")
        self._vm.start_time = value
        self._txt_start.setText(f"{value:.{self._dec}f}")

    def _on_txt_end_changed(self) -> None:
        try:
            value = float(self._txt_end.text())
        except ValueError:
            self._logger.warning(f"Invalid end time input: {self._txt_end.text()}")
            self._txt_end.setText(f"{self._vm.end_time:.{self._dec}f}")
            return

        self._logger.debug(f"UI event: end_time changed -> {value:.6f}")
        self._vm.end_time = value
        self._txt_end.setText(f"{value:.{self._dec}f}")

    def resizeEvent(self, event) -> None:
        self._canvas.draw_idle()
        super().resizeEvent(event)

    def _on_theme_applied(self) -> None:
        self._apply_toolbar_icons()

    def _apply_toolbar_icons(self) -> None:
        if not hasattr(self, "_toolbar"):
            return

        app_theme = QCoreApplication.instance().property("appTheme")
        icon_color = QColor("#17212b") if app_theme == "light" else QColor("#e2e8f0")

        image_keys = {}
        for item in getattr(self._toolbar, "toolitems", []):
            if not item:
                continue
            text, _tooltip, image_file, _callback = item
            if text and image_file:
                image_keys[text] = image_file

        for action in self._toolbar.actions():
            key = image_keys.get(action.text())
            if key is None:
                continue

            icon = self._build_tinted_icon(key, icon_color)
            if not icon.isNull():
                action.setIcon(icon)

    @staticmethod
    def _build_tinted_icon(image_key: str, color: QColor) -> QIcon:
        candidates = [
            Path(cbook._get_data_path("images", f"{image_key}.png")),
            Path(cbook._get_data_path("images", f"{image_key}_large.png")),
            Path(cbook._get_data_path("images", f"{image_key}.svg")),
        ]

        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            return QIcon()

        pixmap = QPixmap(str(source))
        if pixmap.isNull():
            return QIcon()

        tinted = QPixmap(pixmap.size())
        tinted.fill(QColor(0, 0, 0, 0))

        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()

        return QIcon(tinted)
