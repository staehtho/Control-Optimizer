from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from functools import partial
from dataclasses import dataclass, field
import math

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QLineEdit, QSizePolicy, QGridLayout
from PySide6.QtCore import QCoreApplication, QSize, Qt
from PySide6.QtGui import QDoubleValidator, QColor, QPainter, QPixmap, QIcon
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib import cbook

from app_types import PlotField, ConnectSignalConfig
from views import ViewMixin
from views.widgets.toggle_switch import ToggleSwitch, TextPosition

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import PlotViewModel
    from views.widgets import SectionFrame


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
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    subplot: tuple[int, int] = (1, 1)
    subplot_configuration: dict[int, SubplotConfiguration] = field(default_factory=dict)
    show_x_min: bool = True
    show_x_max: bool = True
    # Width / height ratio for a fixed-size canvas. Set None to allow free resizing.
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
                 parent: QWidget = None):
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

        # Matplotlib figure and canvas
        self._figure = Figure(constrained_layout=True)
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

    def _create_header(self) -> QGridLayout:
        """Create the header row with min/max x-values and grid checkbox."""
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        row = 0

        # Grid switch, left-aligned
        self._chk_grid = ToggleSwitch("", TextPosition.Left, self)
        self._chk_grid.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._chk_grid, row, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.field_widgets.setdefault(PlotField.GRID, self._chk_grid)

        for key, show in zip([PlotField.X_MIN, PlotField.X_MAX], [self._cfg.show_x_min, self._cfg.show_x_max]):
            row += 1
            lbl = QLabel("", self)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            lbl.setVisible(show)
            layout.addWidget(lbl, row, 0, alignment=Qt.AlignmentFlag.AlignLeft)
            self.labels.setdefault(key, lbl)

            txt = QLineEdit(self)
            txt.setFixedWidth(90)
            txt.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            txt.setValidator(QDoubleValidator())
            txt.setVisible(show)
            layout.addWidget(txt, row, 1, alignment=Qt.AlignmentFlag.AlignLeft)
            self.field_widgets.setdefault(key, txt)

        # Series row (checkboxes for data visibility)
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)
        self._series_layout = QGridLayout()
        frame_layout.addLayout(self._series_layout)
        layout.addWidget(frame, 0, 2, row + 2, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        self._series_frame = frame

        # add a stretch column at the end to avoid extra spacing
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(row + 1, 1)

        return layout

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""

        # Define key variables for readability
        k_x_min = PlotField.X_MIN
        k_x_max = PlotField.X_MAX
        k_grid = PlotField.GRID

        configs = [
            ConnectSignalConfig(
                key=k_x_min,
                signal_name="editingFinished",
                attr_name="_vm.x_min",
                widget=self.field_widgets.get(k_x_min),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_x_max,
                signal_name="editingFinished",
                attr_name="_vm.x_max",
                widget=self.field_widgets.get(k_x_max),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_grid,
                signal_name="toggled",
                attr_name="_vm.grid",
                widget=self.field_widgets.get(k_grid),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
        ]
        self._connect_object_signals(configs)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # Thread-safe call to update plot
        self._vm.validationFailed.connect(self._on_validation_failed)
        self._vm.gridChanged.connect(self._update_plot)
        self._vm.dataChanged.connect(self._update_plot)
        self._vm.xMinChanged.connect(self._update_plot)
        self._vm.xMaxChanged.connect(self._update_plot)
        self._vm.saveSvgRequested.connect(self.save_svg)

        # Define key variables for readability
        k_x_min = PlotField.X_MIN
        k_x_max = PlotField.X_MAX

        configs = [
            ConnectSignalConfig(
                key=k_x_min,
                signal_name="xMinChanged",
                attr_name="x_min",
                widget=self._vm,
                kwargs={"field": self.field_widgets.get(k_x_min)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_x_max,
                signal_name="xMaxChanged",
                attr_name="x_max",
                widget=self._vm,
                kwargs={"field": self.field_widgets.get(k_x_max)},
                main_event_handler=self._on_vm_changed,
            ),
        ]
        self._connect_object_signals(configs)
    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._chk_grid.setText(self.tr("plot.grid"))
        self.labels.get(PlotField.X_MIN).setText(self.tr("plot.start"))
        self.labels.get(PlotField.X_MAX).setText(self.tr("plot.end"))
        self.field_widgets.get(PlotField.X_MIN).setToolTip(self.tr("plot.start.tooltip"))
        self.field_widgets.get(PlotField.X_MAX).setToolTip(self.tr("plot.end.tooltip"))

        self._series_frame.setText(self.tr("plot.legend"))

        self._vm.retranslate_labels(self._enum_translation)
        self._update_plot()

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self.field_widgets.get(PlotField.X_MIN).setText(self._format_value(self._vm.x_min))
        self.field_widgets.get(PlotField.X_MAX).setText(self._format_value(self._vm.x_max))
        self._chk_grid.setChecked(self._vm.grid)
        # Ensure initial layout is consistent even with no data plotted yet.
        self._update_plot()

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
        data = self._vm.get_data()
        self._sync_series_checkboxes(data)
        self.logger.debug(f"Plot contains {len(data)} data series")

        sorted_series = sorted(data.values(), key=lambda s: s.plot_style.plot_order)
        visible_series = [s for s in sorted_series if s.show and not s.ignore_plot]
        if not visible_series:
            self._figure.suptitle(QCoreApplication.translate(context, self._cfg.title))
            self._canvas.draw_idle()
            return
        active_positions = self._get_active_subplot_positions(sorted_series)
        subplot = self._cfg.subplot
        rows, cols = subplot
        if rows < 1 or cols < 1:
            self.logger.warning(f"Invalid subplot layout {subplot}, falling back to (1, 1)")
            rows, cols = 1, 1

        total_active = max(1, len(active_positions))
        cols = min(cols, total_active)
        rows = max(1, int(math.ceil(total_active / cols)))
        axs = [self._figure.add_subplot(rows, cols, i) for i in range(1, total_active + 1)]
        axis_positions = active_positions if active_positions else [1]
        position_to_index = {pos: idx for idx, pos in enumerate(axis_positions)}

        self._plot_series_on_axes(axs, sorted_series, position_to_index)

        translated_x_labels: list[str] = []

        for i in range(len(axs)):
            position = axis_positions[i]
            subplot_cfg = self._cfg.subplot_configuration.get(position, SubplotConfiguration())
            if len(axs) == 1 and not self._cfg.subplot_configuration:
                x_label = self._cfg.x_label
                y_label = self._cfg.y_label
            else:
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

        self._canvas.draw_idle()

    # ============================================================
    # Helper plotting method (override in subclass)
    # ============================================================
    def _plot_series_on_axes(self, axs, series: list, position_to_index: dict[int, int]) -> None:
        for i in range(len(axs)):
            for serie in series:
                if not serie.show or serie.ignore_plot:
                    continue

                if len(axs) != 1:
                    subplot_position = serie.subplot_position
                    target_index = position_to_index.get(subplot_position)
                    if target_index is None:
                        continue
                    if target_index != i:
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

    def _get_active_subplot_positions(self, series: list) -> list[int]:
        active_positions: list[int] = []
        for serie in series:
            if not serie.show or serie.ignore_plot:
                continue
            pos = serie.subplot_position if serie.subplot_position and serie.subplot_position > 0 else 1
            if pos not in active_positions:
                active_positions.append(pos)
        return active_positions

    def _apply_grid(self, ax) -> None:
        ax.grid(self._vm.grid)

    # ============================================================
    # Series checkboxes synchronization
    # ============================================================
    def _sync_series_checkboxes(self, data: dict) -> None:
        """Synchronize UI checkboxes with current data series visibility."""
        existing_keys = set(self._series_checkboxes.keys())
        sorted_series = sorted(data.values(), key=lambda s: s.plot_style.plot_order)

        insert_index = 0
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
            self._series_layout.addWidget(checkbox, insert_index // 3, insert_index % 3)
            insert_index += 1
            existing_keys.discard(series.key)

        # Remove leftover checkboxes
        for key in existing_keys:
            checkbox = self._series_checkboxes.pop(key)
            self._series_layout.removeWidget(checkbox)
            checkbox.deleteLater()
            self.field_widgets.pop(f"plot_data_{key}", None)

        # Hide the checkbox and label when there is only one series.
        self._series_frame.setVisible(len(self._series_checkboxes) > 1)

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

    def save_svg(self, path: str | Path) -> None:
        """Save the current plot to an SVG file."""
        target = Path(path)
        if target.suffix.lower() != ".svg":
            target = target.with_suffix(".svg")
        self._figure.savefig(target, format="svg", bbox_inches="tight")

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
