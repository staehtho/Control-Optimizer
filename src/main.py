import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app_domain import AppEngine
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import FunctionTypes
from app_types import ThemeType
from views import (
    PlantView, FunctionView, ControllerView, PsoConfigurationView, EvaluationView, MainView, BaseView,
    SimulationView, SettingsView
)
from views.widgets import NavItem
from views.translations import NavLabels

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
        "frequency_domain": engine.ensure_bode_plot_viewmodel("frequency_domain_evaluation")
    }

    items = [
        NavItem(NavLabels.PLANT, {
            ThemeType.DARK: "plant_dark.svg", ThemeType.LIGHT: "plant_light.svg"
        }),
        NavItem(NavLabels.EXCITATION_FUNCTION, {
            ThemeType.DARK: "excitation_function_dark.svg", ThemeType.LIGHT: "excitation_function_light.svg"
        }),
        NavItem(NavLabels.CONTROLLER, {
            ThemeType.DARK: "controller_dark.svg", ThemeType.LIGHT: "controller_light.svg"
        }),
        NavItem(NavLabels.PSO_PARAMETER, {
            ThemeType.DARK: "pso_parameter_dark.svg", ThemeType.LIGHT: "pso_parameter_light.svg"
        }),
        NavItem(NavLabels.EVALUATION, {
            ThemeType.DARK: "evaluation_dark.svg", ThemeType.LIGHT: "evaluation_light.svg"
        }),
        NavItem(NavLabels.SIMULATION, {
            ThemeType.DARK: "simulation_dark.svg", ThemeType.LIGHT: "simulation_light.svg"
        }),
        NavItem(NavLabels.SETTINGS, {
            ThemeType.DARK: "settings_dark.svg", ThemeType.LIGHT: "settings_light.svg"
        }),
    ]

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
        ),
        NavLabels.SETTINGS: lambda parent=None: SettingsView(ui_context, parent=parent),
    }

    main_view = MainView(ui_context, items, view_factories, engine.vm_pso)
    main_view.show()

    sys.exit(app.exec())
