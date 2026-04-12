from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QT_TRANSLATE_NOOP
import numpy as np
from matplotlib.ticker import LogLocator
from pytestqt.qtbot import QWidget

from app_types import BodePlotData
from .plot_widget import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import PlotViewModel

class BodePlotWidget(PlotWidget):
    """Widget for displaying a Bode plot.

    The widget consists of two vertically stacked subplots:
        1. Margin plot (gain in dB)
        2. Phase plot (in degrees)

    The data series passed from the PlotViewModel must contain:
        - omega: frequency values
        - margin: gain values (in dB)
        - phase: phase values (in degrees)
        - label: legend label
        - plot_style: matplotlib styling configuration
    """

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext, vm: PlotViewModel, parent: QWidget = None):
        """Initialize the BodePlotWidget.

        Args:
            ui_context: Shared UI context used across the application.
            vm: PlotViewModel providing the plot series.
            parent: Optional Qt parent object.
        """

        # Configuration of the two subplots
        subplot_cfgs = {
            1: SubplotConfiguration(
                title=str(QT_TRANSLATE_NOOP("BodePlotWidget", "Margin")),
                x_label=str(QT_TRANSLATE_NOOP("BodePlotWidget", "Frequency /rad/s")),
                position=1
            ),
            2: SubplotConfiguration(
                title=str(QT_TRANSLATE_NOOP("BodePlotWidget", "Phase")),
                x_label=str(QT_TRANSLATE_NOOP("BodePlotWidget", "Frequency /rad/s")),
                position=2
            ),
        }

        # Global configuration for the PlotWidget base class
        plt_cfg = PlotWidgetConfiguration(
            context="BodePlotWidget",
            subplot=(2, 1),
            subplot_configuration=subplot_cfgs,
        )

        super().__init__(ui_context, vm, plt_cfg, parent)

    # ============================================================
    # Plotting
    # ============================================================

    def _plot_series_on_axes(self, axs, series: list, position_to_index: dict[int, int] | None = None) -> None:
        """Plot all provided series on the Bode axes.

        This method delegates the actual drawing to helper methods
        and ensures that legends are created if labels are available.

        Args:
            axs: List of matplotlib axes (margin axis, phase axis).
            series: List of data series to plot.
            position_to_index: Optional mapping of subplot position to axis index (unused).
        """

        # Plot margin and phase curves
        self._plot_margin_and_phase_on_axes(axs, series)

        # Add legends if plot labels exist
        handles, labels = axs[0].get_legend_handles_labels()
        if handles:
            legend = axs[0].legend(loc="best", frameon=False)
            legend.set_draggable(True)

    def _apply_grid(self, ax) -> None:
        if self._vm.grid:
            # Major ticks at 10^n
            ax.xaxis.set_major_locator(LogLocator(base=10))

            # Minor ticks at 2–9 * 10^n
            ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1))

            # Gridlines
            ax.grid(True, which='major', linestyle='-')
            ax.grid(True, which='minor', linestyle='--', alpha=0.5)
        else:
            ax.grid(False)


    def _plot_margin_and_phase_on_axes(self, axs, series: list) -> None:
        """Plot margin and phase responses on the Bode axes.

        The margin curve is plotted on the first axis and the phase
        curve on the second axis using a logarithmic frequency scale.

        The method also computes automatic y-axis scaling.

        Args:
            axs: List containing margin and phase matplotlib axes.
            series: List of series objects to plot.
        """

        ax_margin = axs[0]
        ax_phase = axs[1]

        all_margin = []

        for serie in series:
            if not isinstance(serie, BodePlotData):
                raise TypeError("BodePlotWidget expects BodeSeries objects.")

            if not serie.show or serie.ignore_plot:
                continue

            self.logger.debug(f"Plotting margin and phase: {serie.key}")

            # Plot margin (gain) curve
            ax_margin.semilogx(
                serie.omega,
                serie.margin,
                label=serie.label,
                zorder=len(series) - serie.plot_style.z_order + 1,
                **serie.plot_style.mpl_kwargs(),
            )

            all_margin.append(serie.margin)

            # Wrap phase into range [-180�, 180�]
            phase = (serie.phase + 180) % 360 - 180

            # Plot phase curve
            ax_phase.semilogx(
                serie.omega,
                phase,
                label=serie.label,
                zorder=len(series) - serie.plot_style.z_order + 1,
                **serie.plot_style.mpl_kwargs(),
            )

        if len(all_margin) == 0:
            all_margin.append(np.logspace(-5, 5, 20))

        # Flatten margin arrays to determine global limits
        all_margin = np.hstack(all_margin)

        # ---- Margin axis autoscaling ----

        # Round bounds to multiples of 20 dB
        margin_min = np.floor(all_margin.min() / 20) * 20
        margin_max = np.ceil(all_margin.max() / 20) * 20 + 20

        # Determine tick spacing
        step = max(20, (abs(margin_max) + abs(margin_min)) // 6 // 20 * 20)

        # Ensure the 0 dB line is visible
        margin_min += step - (margin_min % step)

        ax_margin.set_yticks(np.arange(margin_min, margin_max + 1, step))

        # ---- Phase axis autoscaling ----

        # Standard phase tick spacing for Bode plots
        ax_phase.set_yticks(np.arange(-180, 181, 45))

    def _get_active_subplot_positions(self, series: list) -> list[int]:
        # Bode plot always needs margin + phase axes even if no data is visible.
        return [1, 2]
