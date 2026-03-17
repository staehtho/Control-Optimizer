from pathlib import Path
from functools import partial
from dataclasses import dataclass, field

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QSizePolicy
)
from PySide6.QtCore import QCoreApplication, QObject, QSize
from PySide6.QtGui import QDoubleValidator, QColor, QPainter, QPixmap, QIcon
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib import cbook

from app_domain.ui_context import UiContext
from app_types import PlotField
from viewmodels import PlotViewModel
from views import ViewMixin
from views.widgets.toggle_switch import ToggleSwitch


@dataclass
class SubplotConfiguration:
    """Configuration for individual subplots."""
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    position: int = 1


@dataclass
class PlotWidgetConfiguration:
    """Configuration for the overall plot widget."""
    context: str
    title: str
    x_label: str = ""
    y_label: str = ""
    subplot: tuple[int, int] = (1, 1)
    subplot_configuration: dict[int, SubplotConfiguration] = field(default_factory=dict)
    show_x_min_max: bool = True
    # Width / height ratio for a fixed-size canvas. Set to None to allow free resizing.
    fixed_aspect_ratio: float | None = 500 / 350


class PlotWidget(ViewMixin, QWidget):
    """Generic plotting widget with matplotlib canvas, toolbar, and series checkboxes.

    Attributes:
        _vm (PlotViewModel): ViewModel providing data and plot settings.
        _cfg (PlotWidgetConfiguration): Plot widget configuration.
        _series_checkboxes (dict[str, QCheckBox]): Mapping of series keys to checkboxes.
    """

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext, vm: PlotViewModel,
                 plot_configuration: PlotWidgetConfiguration,
                 parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm = vm
        self._cfg = plot_configuration
        self._series_checkboxes: dict[str, QCheckBox] = {}

        ViewMixin.__init__(self, ui_context)

        self.logger.debug(f"PlotWidget initialized (context={self._cfg.context})")

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Header row (start/end x values, grid toggle)
        header_layout = self._create_header()
        main_layout.addLayout(header_layout, 0)

        # Series row (checkboxes for data visibility)
        series_layout = self._create_series_row()
        main_layout.addLayout(series_layout, 0)

        # Matplotlib figure and canvas
        self._figure = Figure()
        if self._cfg.fixed_aspect_ratio:
            self._canvas = _AspectCanvas(self._figure, self._cfg.fixed_aspect_ratio)
        else:
            self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self._cfg.fixed_aspect_ratio:
            policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            policy.setHeightForWidth(True)
            self._canvas.setSizePolicy(policy)
            min_width = 500
            min_height = int(round(min_width / self._cfg.fixed_aspect_ratio))
            self._canvas.setMinimumSize(min_width, max(1, min_height))
        else:
            self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._canvas.setMinimumSize(500, 350)
        self._apply_toolbar_icons()

        main_layout.addWidget(self._toolbar, 0)
        main_layout.addWidget(self._canvas, 1)

        self.setLayout(main_layout)

    def _create_header(self) -> QHBoxLayout:
        """Create the header row with min/max x-values and grid checkbox."""
        layout = QHBoxLayout()
        show = self._cfg.show_x_min_max

        # Start time
        self._lbl_min = QLabel("", self)
        self._lbl_min.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._lbl_min.setVisible(show)
        layout.addWidget(self._lbl_min)

        self._txt_min = QLineEdit(self)
        self._txt_min.setFixedWidth(90)
        self._txt_min.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._txt_min.setValidator(QDoubleValidator())
        self._txt_min.setVisible(show)
        layout.addWidget(self._txt_min)
        self.field_widgets.setdefault(PlotField.X_MIN, self._txt_min)

        # End time
        self._lbl_max = QLabel("", self)
        self._lbl_max.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._lbl_max.setVisible(show)
        layout.addWidget(self._lbl_max)

        self._txt_max = QLineEdit(self)
        self._txt_max.setFixedWidth(90)
        self._txt_max.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._txt_max.setValidator(QDoubleValidator())
        self._txt_max.setVisible(show)
        layout.addWidget(self._txt_max)
        self.field_widgets.setdefault(PlotField.X_MAX, self._txt_max)

        # Grid switch
        self._chk_grid = ToggleSwitch("", self)
        self._chk_grid.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._chk_grid)
        self.field_widgets.setdefault(PlotField.GRID, self._chk_grid)

        layout.addStretch()  # keeps everything left-aligned
        return layout

    def _create_series_row(self) -> QHBoxLayout:
        """Create the series checkbox row."""
        layout = QHBoxLayout()
        self._lbl_series = QLabel("Data:", self)
        self._lbl_series.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._lbl_series)
        layout.addStretch()
        self._series_layout = layout
        return layout

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[PlotField, tuple[str, str, object]] = {
            PlotField.X_MIN: ("editingFinished", "_vm.x_min", float),
            PlotField.X_MAX: ("editingFinished", "_vm.x_max", float),
            PlotField.GRID: ("toggled", "_vm.grid", bool),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self.field_widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # Thread-safe call to update plot
        self._vm.validationFailed.connect(self._on_validation_failed)
        self._vm.gridChanged.connect(self._update_plot)
        self._vm.dataChanged.connect(self._update_plot)
        self._vm.xMinChanged.connect(partial(self._on_vm_changed, PlotField.X_MIN, "_vm.x_min"))
        self._vm.xMaxChanged.connect(partial(self._on_vm_changed, PlotField.X_MAX, "_vm.x_max"))

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._chk_grid.setText(self.tr("plot.grid"))
        self._lbl_min.setText(self.tr("plot.start"))
        self._lbl_max.setText(self.tr("plot.end"))
        self._txt_min.setToolTip(self.tr("plot.start.tooltip"))
        self._txt_max.setToolTip(self.tr("plot.end.tooltip"))

        self._vm.retranslate_labels(self._enum_translation)
        self._update_plot()

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._txt_min.setText(self._format_value(self._vm.x_min))
        self._txt_max.setText(self._format_value(self._vm.x_max))
        self._chk_grid.setChecked(self._vm.grid)

    # ============================================================
    # Plot update
    # ============================================================
    def _update_plot(self) -> None:
        """Redraw the plot, including axes, legends, and grid."""
        self.logger.debug(
            f"Updating plot (grid={self._vm.grid}, xlim=[{self._vm.x_min}, {self._vm.x_max}])"
        )

        context = self._cfg.context
        tr = lambda text: QCoreApplication.translate(context, text) if text else text

        self._figure.clear()
        subplot = self._cfg.subplot
        rows, cols = subplot
        if rows < 1 or cols < 1:
            self.logger.warning(f"Invalid subplot layout {subplot}, falling back to (1, 1)")
            rows, cols = 1, 1
        total_subplots = rows * cols
        axs = [self._figure.add_subplot(rows, cols, i) for i in range(1, total_subplots + 1)]

        data = self._vm.get_data()
        self._sync_series_checkboxes(data)
        self.logger.debug(f"Plot contains {len(data)} data series")

        sorted_series = sorted(data.values(), key=lambda s: s.plot_style.plot_order)

        self._plot_series_on_axes(axs, sorted_series)

        translated_x_labels: list[str] = []

        for i in range(len(axs)):
            if len(axs) == 1:
                x_label = self._cfg.x_label
                y_label = self._cfg.y_label
            else:
                subplot_cfg = self._cfg.subplot_configuration.get(i + 1, SubplotConfiguration())
                x_label = subplot_cfg.x_label or self._cfg.x_label
                y_label = subplot_cfg.y_label or self._cfg.y_label

                axs[i].set_title(tr(subplot_cfg.title))

            translated_x = tr(x_label)
            translated_y = tr(y_label)
            translated_x_labels.append(translated_x)
            axs[i].set_xlabel(translated_x)
            axs[i].set_ylabel(translated_y)
            if len(axs) > 1:
                axs[i].xaxis.labelpad = 10

            self._apply_grid(axs[i])
            axs[i].set_xlim(self._vm.x_min, self._vm.x_max)

        same_x_labels = len(axs) > 1 and len({label.strip() for label in translated_x_labels}) == 1
        if same_x_labels:
            lowest_idx = len(axs) - 1
            for i, ax in enumerate(axs):
                if i != lowest_idx:
                    ax.set_xlabel("")
                    ax.tick_params(axis="x", which="both", labelbottom=False)
                else:
                    ax.tick_params(axis="x", which="both", labelbottom=True)

        self._figure.suptitle(QCoreApplication.translate(context, self._cfg.title))
        # Reserve enough margin for x-axis labels in framed layouts.
        bottom = 0.16
        if len(axs) == 1:
            hspace = 0.35
        elif same_x_labels:
            hspace = 0.20
        else:
            hspace = 0.60
        self._figure.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=bottom, hspace=hspace)

        self._canvas.draw_idle()

    # ============================================================
    # Helper plotting method (override in subclass)
    # ============================================================
    def _plot_series_on_axes(self, axs, series: list) -> None:
        for i in range(len(axs)):
            for serie in series:
                if not serie.show or serie.ignore_plot:
                    continue

                if len(axs) != 1:
                    subplot_position = serie.subplot_position
                    if subplot_position < 1 or subplot_position > len(axs):
                        self.logger.warning(
                            f"Series '{serie.key}' has invalid subplot position {subplot_position}; "
                            "using subplot 1"
                        )
                        subplot_position = 1
                    if subplot_position != i + 1:
                        continue

                self.logger.debug(f"Plotting serie: {serie.key}")
                axs[i].plot(
                    serie.x,
                    serie.y,
                    label=serie.label,
                    zorder=len(series) - serie.plot_style.z_order + 1,
                    **serie.plot_style.mpl_kwargs(),
                )

            handles, labels = axs[i].get_legend_handles_labels()
            if handles:
                legend = axs[i].legend(loc="best", frameon=False)
                legend.set_draggable(True)

    def _apply_grid(self, ax) -> None:
        ax.grid(self._vm.grid)

    # ============================================================
    # Series checkboxes synchronization
    # ============================================================
    def _sync_series_checkboxes(self, data: dict) -> None:
        """Synchronize UI checkboxes with current data series visibility."""
        existing_keys = set(self._series_checkboxes.keys())
        sorted_series = sorted(data.values(), key=lambda s: s.plot_style.z_order)

        insert_index = 1
        for series in sorted_series:
            if series.ignore_plot:
                checkbox = self._series_checkboxes.pop(series.key, None)
                if checkbox is not None:
                    self._series_layout.removeWidget(checkbox)
                    checkbox.deleteLater()
                    self.field_widgets.pop(f"plot_data_{series.key}", None)
                existing_keys.discard(series.key)
                continue

            checkbox = self._series_checkboxes.get(series.key)
            if checkbox is None:
                checkbox = QCheckBox(series.label, self)
                checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                checkbox.toggled.connect(partial(self._on_series_checkbox_toggled, series.key))
                self._series_checkboxes[series.key] = checkbox
                self.field_widgets[f"plot_data_{series.key}"] = checkbox
            else:
                checkbox.setText(series.label)

            if checkbox.isChecked() != series.show:
                checkbox.setChecked(series.show)

            self._series_layout.removeWidget(checkbox)
            self._series_layout.insertWidget(insert_index, checkbox)
            insert_index += 1
            existing_keys.discard(series.key)

        # Remove leftover checkboxes
        for key in existing_keys:
            checkbox = self._series_checkboxes.pop(key)
            self._series_layout.removeWidget(checkbox)
            checkbox.deleteLater()
            self.field_widgets.pop(f"plot_data_{key}", None)

        # Hide the checkbox and label when there is only one series.
        self._lbl_series.setVisible(len(self._series_checkboxes) > 1)

        if len(self._series_checkboxes) == 1:
            next(iter(self._series_checkboxes.values())).setVisible(False)
        else:
            for checkbox in self._series_checkboxes.values():
                checkbox.setVisible(True)

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_series_checkbox_toggled(self, key: str, checked: bool) -> None:
        self.logger.debug(f"UI event: series visibility changed -> {key}={checked}")
        self._vm.set_data_visibility(key, checked)

    def resizeEvent(self, event) -> None:
        """Redraw canvas on widget resize."""
        self._canvas.draw_idle()
        super().resizeEvent(event)

    # ============================================================
    # Theme handling
    # ============================================================
    def _on_theme_applied(self) -> None:
        self._apply_toolbar_icons()

    def _apply_toolbar_icons(self) -> None:
        """Apply toolbar icons tinted according to current theme."""
        if not hasattr(self, "_toolbar"):
            return

        app = QCoreApplication.instance()
        icon_color = app.property("themeTextColor")
        if not isinstance(icon_color, QColor) or not icon_color.isValid():
            icon_color = self.palette().color(self.foregroundRole())

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
        """Load a toolbar icon and apply color tint."""
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
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return QIcon(tinted)


class _AspectCanvas(FigureCanvas):
    """Figure canvas that keeps a fixed width/height ratio via height-for-width."""

    def __init__(self, figure: Figure, ratio: float):
        super().__init__(figure)
        self._ratio = ratio if ratio and ratio > 0 else 1.0

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return int(round(width / self._ratio))

    def sizeHint(self) -> QSize:
        width = 500
        height = int(round(width / self._ratio))
        return QSize(width, max(1, height))
