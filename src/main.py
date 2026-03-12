import logging
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app_domain import AppEngine
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import FunctionTypes
from app_types import NavItem, NavLabels
from views.main_view import MainView

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

    engine = AppEngine(run_warmup=False)
    app.aboutToQuit.connect(engine.shutdown)
    ui_context = engine.ui_context

    vm_function = engine.ensure_function_viewmodel("excitation_target")
    vm_function.set_selected_function(FunctionTypes.STEP)

    items = [
        NavItem(NavLabels.PLANT, "plant.svg"),
        NavItem(NavLabels.EXCITATION_FUNCTION, "excitation_function.svg"),
        NavItem(NavLabels.CONTROLLER, "controller.svg"),
        NavItem(NavLabels.PSO_PARAMETER, "pso_parameter.svg"),
        NavItem(NavLabels.EVALUATION, "evaluation.svg"),
        NavItem(NavLabels.SIMULATION, "simulation.svg"),
        NavItem(NavLabels.SETTINGS, "settings.svg", bottom=True),
    ]


    def _create_plant_view(parent=None):
        from views.plant_view import PlantView
        return PlantView(ui_context, engine.vm_plant, engine.ensure_plot_viewmodel("plant"), parent=parent)


    def _create_function_view(parent=None):
        from views.function_view import FunctionView
        return FunctionView(
            ui_context, engine.ensure_function_viewmodel("excitation_target"),
            engine.ensure_plot_viewmodel("function"), parent=parent
        )


    def _create_controller_view(parent=None):
        from views.controller_view import ControllerView
        return ControllerView(ui_context, engine.vm_controller, parent=parent)


    def _create_pso_configuration_view(parent=None):
        from views.pso_configuration_view import PsoConfigurationView
        return PsoConfigurationView(
            ui_context, engine.vm_plant, engine.ensure_function_viewmodel("excitation_target"), engine.vm_pso,
            parent=parent
        )


    def _create_evaluation_view(parent=None):
        from views.evaluation_view import EvaluationView
        vm_plots = {
            "time_domain": engine.ensure_plot_viewmodel("time_domain_evaluation"),
            "frequency_domain": engine.ensure_bode_plot_viewmodel("frequency_domain_evaluation")
        }
        return EvaluationView(ui_context, engine.vm_evaluator, vm_plots, parent=parent)


    def _create_simulation_view(parent=None):
        from views.simulation_view import SimulationView
        vm_functions = {title.name: engine.ensure_function_viewmodel(title.name) for title in ExcitationTarget}
        return SimulationView(
            ui_context, engine.vm_simulation, vm_functions, engine.ensure_plot_viewmodel("time_domain_simulation"),
            parent=parent
        )


    def _create_settings_view(parent=None):
        from views.settings_view import SettingsView
        return SettingsView(ui_context, parent=parent)


    view_factories = {
        NavLabels.PLANT: _create_plant_view,
        NavLabels.EXCITATION_FUNCTION: _create_function_view,
        NavLabels.CONTROLLER: _create_controller_view,
        NavLabels.PSO_PARAMETER: _create_pso_configuration_view,
        NavLabels.EVALUATION: _create_evaluation_view,
        NavLabels.SIMULATION: _create_simulation_view,
        NavLabels.SETTINGS: _create_settings_view,
    }

    main_view = MainView(ui_context, items, view_factories, engine.vm_pso)
    main_view.show()

    QTimer.singleShot(0, lambda: engine.run_warmup(2))

    sys.exit(app.exec())
