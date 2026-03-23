import logging
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# TODO: add buttons to switch to the next or previous view in the view it self
# TODO: TabIndex

# TODO: BodePlot: when all plots are disabled, the y-axis should not be rescaled. now it scale to 99999 or so :)

# TODO: Controller: move the block diagram and the selection of the anti windup in one section called anti windup
#  and call the selection method or so

# TODO: PSO: overshoot only for step

# TODO: Evaluation: block diagram add l and n input
# TODO: Evaluation: TF with L and N
# TODO: Evaluation: clean TF of C, G, etc.

def main():
    from app_domain import AppEngine
    from app_domain.functions import FunctionTypes
    from app_types import NavItem, NavLabels
    from views.main_view import MainView
    from views.resources import Icons, SRC_DIR

    # init logging
    log_dir = Path(SRC_DIR) / "logs"
    log_file = log_dir / "app.log"

    log_dir.mkdir(parents=True, exist_ok=True)
    # delete log file
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
        logger.setLevel(logging.CRITICAL + 1)

    app = QApplication(sys.argv)

    engine = AppEngine(run_warmup=False)
    app.aboutToQuit.connect(engine.shutdown)
    ui_context = engine.ui_context

    items = [
        NavItem(NavLabels.PLANT, Icons.plant),
        NavItem(NavLabels.EXCITATION_FUNCTION, Icons.excitation_function),
        NavItem(NavLabels.CONTROLLER, Icons.controller),
        NavItem(NavLabels.PSO_PARAMETER, Icons.pso_parameter),
        NavItem(NavLabels.EVALUATION, Icons.evaluation),
        NavItem(NavLabels.SIMULATION, Icons.simulation),
        NavItem(NavLabels.SETTINGS, Icons.settings, bottom=True),
    ]

    def _vm_function():
        vm_function = engine.ensure_function_viewmodel("excitation_target")
        vm_function.set_selected_function(FunctionTypes.STEP)
        return vm_function

    def _create_plant_view(parent=None):
        from views.plant_view import PlantView
        return PlantView(
            ui_context,
            engine.ensure_plant_viewmodel(),
            engine.ensure_plot_viewmodel("plant"),
            parent=parent
        )

    def _create_function_view(parent=None):
        from views.function_view import FunctionView
        return FunctionView(
            ui_context,
            _vm_function(),
            engine.ensure_plot_viewmodel("function"),
            parent=parent
        )

    def _create_controller_view(parent=None):
        from views.controller_view import ControllerView
        return ControllerView(ui_context, engine.ensure_controller_viewmodel(), parent=parent)

    def _create_pso_configuration_view(parent=None):
        from views.pso_configuration_view import PsoConfigurationView
        return PsoConfigurationView(
            ui_context,
            engine.ensure_plant_viewmodel(),
            _vm_function(),
            engine.ensure_pso_viewmodel(),
            parent=parent
        )

    def _create_evaluation_view(parent=None):
        from views.evaluation_view import EvaluationView
        vm_plots = {
            "time_domain": engine.ensure_plot_viewmodel("time_domain_evaluation"),
            "frequency_domain": engine.ensure_bode_plot_viewmodel("frequency_domain_evaluation")
        }
        return EvaluationView(ui_context, engine.ensure_evaluator_viewmodel(), vm_plots, parent=parent)

    def _create_simulation_view(parent=None):
        from views.simulation_view import SimulationView
        from app_domain.controlsys import ExcitationTarget
        vm_functions = {title.name: engine.ensure_function_viewmodel(title.name) for title in ExcitationTarget}
        return SimulationView(
            ui_context,
            engine.ensure_simulation_viewmodel(),
            vm_functions,
            engine.ensure_plot_viewmodel("time_domain_simulation"),
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

    main_view = MainView(ui_context, items, view_factories, engine.ensure_pso_viewmodel())
    main_view.show()

    QTimer.singleShot(750, lambda: engine.run_warmup(2))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
