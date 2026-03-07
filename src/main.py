import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from app_domain import AppEngine
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import FunctionTypes
from views import PlantView, FunctionView, ControllerView, PsoConfigurationView, EvaluationView, MainView, BaseView, \
    SimulationView
from views.widgets import NavItem
from views.translations import NavLabels


def print_tab_order(parent_widget: QWidget) -> None:
    """
    Print all focusable child widgets of a parent widget in their tab order.

    Args:
        parent_widget: The QWidget containing focusable children.
    """
    # Collect all children that accept focus
    focusable_widgets = [
        w for w in parent_widget.findChildren(QWidget)
        if w.focusPolicy() != Qt.FocusPolicy.NoFocus
    ]

    # Sort by focus order: in Qt, findChildren returns layout order by default,
    # but tab order may be custom via setTabOrder.
    print("Focusable widgets in tab order:")
    for i, w in enumerate(focusable_widgets):
        obj_name = w.objectName() or w.__class__.__name__
        print(f"  Tab index {i}: {obj_name}")

if __name__ == '__main__':

    # init logging
    # Verzeichnis prüfen oder erstellen
    log_dir = Path("log")
    log_file = log_dir / "app.log"

    log_dir.mkdir(parents=True, exist_ok=True)
    # log_file löschen, falls vorhanden
    if log_file.exists():
        log_file.unlink()

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    for log in ("matplotlib.font_manager", "numba.core.ssa", "numba.core.byteflow", "numba.core.interpreter",
                "matplotlib.ticker"):
        logger = logging.getLogger(log)
        old_level = logger.level
        logger.setLevel(logging.CRITICAL + 1)  # nichts wird mehr geloggt

    app = QApplication(sys.argv)

    engine = AppEngine()
    app.aboutToQuit.connect(engine.shutdown)
    ui_context = engine.ui_context
    BaseView.load_themes(ui_context.vm_theme.get_theme_cfg(), ui_context.vm_theme.current_theme)
    ui_context.vm_theme.themeChanged.connect(BaseView.set_theme)

    vm_function = engine.ensure_function_viewmodel("excitation_target")
    vm_function.set_selected_function(FunctionTypes.STEP)

    vm_functions = {title.name: engine.ensure_function_viewmodel(title.name) for title in ExcitationTarget}
    vm_plots = {
        "time_domain": engine.ensure_plot_viewmodel("time_domain_evaluation"),
        "frequency_domain": engine.ensure_plot_viewmodel("frequency_domain_evaluation")
    }

    items = [NavItem(key, "") for key in NavLabels]

    view_factories = {
        NavLabels.PLANT: lambda parent=None: PlantView(
            ui_context, engine.vm_plant, engine.ensure_plot_viewmodel("plant"), parent=parent
        ),
        NavLabels.EXCITATION_FUNCTION: lambda parent=None: FunctionView(
            ui_context, engine.ensure_function_viewmodel("excitation_target"),
            engine.ensure_plot_viewmodel("function"), parent=parent
        ),
        NavLabels.CONTROLLER: lambda parent=None: ControllerView(
            ui_context, engine.vm_controller, parent=parent
        ),
        NavLabels.PSO_PARAMETER: lambda parent=None: PsoConfigurationView(
            ui_context, engine.vm_plant, engine.ensure_function_viewmodel("excitation_target"), engine.vm_pso,
            parent=parent
        ),
        NavLabels.EVALUATION: lambda parent=None: EvaluationView(
            ui_context, engine.vm_evaluator, vm_plots, parent=parent
        ),
        NavLabels.SIMULATION: lambda parent=None: SimulationView(
            ui_context, engine.vm_simulation, vm_functions, engine.ensure_plot_viewmodel("time_domain_simulation"),
            parent=parent
        )
    }

    from views.widgets import BodePlotWidget
    from viewmodels.types import BodePlotData, PlotData
    from app_domain.controlsys import Plant
    from views.plot_style import PLOT_STYLE, PlotLabels
    import numpy as np

    plant = Plant([1], [1, 2, 1])

    omega = np.logspace(-5, 5, 1000)
    s = 1j * omega
    y = plant.system(s)
    mag = 20 * np.log10(np.abs(y)) + 80
    phase = np.angle(y, deg=True)

    marg = BodePlotData(
        key="margin",
        label="Closed Loop",
        omega=omega,
        margin=mag,
        phase=phase,
        plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
    )

    vm = engine.ensure_plot_viewmodel("frequency_domain_simulation")
    vm.x_min = 10 ** (-5)
    vm.x_max = 10 ** 5
    vm.update_data(marg)

    widget = BodePlotWidget(ui_context, engine.ensure_plot_viewmodel("frequency_domain_simulation"))
    widget.show()

    main_view = MainView(ui_context, items, view_factories, engine.vm_pso)
    main_view.show()

    sys.exit(app.exec())
