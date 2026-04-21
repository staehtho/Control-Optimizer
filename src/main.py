import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap, Qt, QIcon
from PySide6.QtWidgets import QApplication, QSplashScreen

from resources.resources import SRC_DIR, TEMP_DIR, LOG_DIR


def create_app():
    return QApplication(sys.argv)


def show_splash():
    path = Path(__file__).parent / "resources" / "icons" / "control_optimizer.svg"

    pixmap = QPixmap(str(path))

    # Scale the pixmap
    pixmap = pixmap.scaled(
        256, 256,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    splash = QSplashScreen(pixmap)
    splash.show()
    return splash


def setup_logging(log_dir, log_level):
    log_file = log_dir / "app.log"

    log_dir.mkdir(parents=True, exist_ok=True)

    if log_file.exists():
        log_file.unlink()

    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    noisy_logs = (
        "matplotlib.font_manager",
        "numba.core.ssa",
        "numba.core.byteflow",
        "numba.core.interpreter",
        "matplotlib.ticker"
    )

    for log in noisy_logs:
        logging.getLogger(log).setLevel(logging.CRITICAL + 1)


def setup_output_directory(output_dir):
    import shutil

    # Remove the directory if it exists
    if output_dir.exists() and output_dir.is_dir():
        shutil.rmtree(output_dir)  # removes non-empty directory safely

    # Recreate the directory
    output_dir.mkdir(parents=True, exist_ok=True)


def create_engine():
    from app_domain import AppEngine
    engine = AppEngine()
    return engine


def connect_shutdown(app, engine):
    app.aboutToQuit.connect(engine.shutdown)


# ---- ViewModel helpers ----

def create_vm_function(engine):
    from app_domain.functions import FunctionTypes
    vm_function = engine.ensure_function_viewmodel("excitation_target")
    vm_function.set_selected_function(FunctionTypes.STEP)
    return vm_function


# ---- View factories ----

def create_view_factories(engine, ui_context):
    from app_types import NavLabels

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
            create_vm_function(engine),
            engine.ensure_plot_viewmodel("function"),
            parent=parent
        )

    def _create_controller_view(parent=None):
        from views.controller_view import ControllerView
        return ControllerView(
            ui_context,
            engine.ensure_controller_viewmodel(),
            parent=parent
        )

    def _create_pso_configuration_view(parent=None):
        from views.pso_configuration_view import PsoConfigurationView
        return PsoConfigurationView(
            ui_context,
            engine.ensure_plant_viewmodel(),
            create_vm_function(engine),
            engine.ensure_controller_viewmodel(),
            engine.ensure_pso_viewmodel(),
            parent=parent
        )

    def _create_evaluation_view(parent=None):
        from views.evaluation_view import EvaluationView
        vm_plots = {
            "time_domain": engine.ensure_plot_viewmodel("time_domain_evaluation"),
            "frequency_domain": engine.ensure_bode_plot_viewmodel("frequency_domain_evaluation")
        }
        return EvaluationView(
            ui_context,
            engine.ensure_evaluator_viewmodel(),
            vm_plots,
            parent=parent
        )

    def _create_simulation_view(parent=None):
        from views.simulation_view import SimulationView
        from app_domain.controlsys import ExcitationTarget

        vm_functions = {
            title.name: engine.ensure_function_viewmodel(title.name)
            for title in ExcitationTarget
        }

        return SimulationView(
            ui_context,
            engine.ensure_simulation_viewmodel(),
            vm_functions,
            engine.ensure_plot_viewmodel("time_domain_simulation"),
            parent=parent
        )

    def _create_data_view(parent=None):
        from views.data_management_view import DataManagementView
        return DataManagementView(ui_context, engine.ensure_data_viewmodel(), parent=parent)

    def _create_help_view(parent=None):
        from views.help_view import HelpView
        return HelpView(ui_context, parent=parent)

    def _create_settings_view(parent=None):
        from views.settings_view import SettingsView
        return SettingsView(ui_context, parent=parent)

    return {
        NavLabels.PLANT: _create_plant_view,
        NavLabels.EXCITATION_FUNCTION: _create_function_view,
        NavLabels.CONTROLLER: _create_controller_view,
        NavLabels.PSO_PARAMETER: _create_pso_configuration_view,
        NavLabels.EVALUATION: _create_evaluation_view,
        NavLabels.SIMULATION: _create_simulation_view,
        NavLabels.DATA_MANAGEMENT: _create_data_view,
        NavLabels.HELP: _create_help_view,
        NavLabels.SETTINGS: _create_settings_view,
    }


def create_main_view(engine, ui_context, view_factories):
    from views.main_view import MainView
    from app_types import NavItem, NavLabels
    from resources.resources import Icons

    items = [
        NavItem(NavLabels.PLANT, Icons.plant),
        NavItem(NavLabels.EXCITATION_FUNCTION, Icons.excitation_function),
        NavItem(NavLabels.CONTROLLER, Icons.controller),
        NavItem(NavLabels.PSO_PARAMETER, Icons.pso_parameter),
        NavItem(NavLabels.EVALUATION, Icons.evaluation),
        NavItem(NavLabels.SIMULATION, Icons.simulation),
        NavItem(NavLabels.DATA_MANAGEMENT, Icons.data_management, bottom=True),
        NavItem(NavLabels.HELP, Icons.help, bottom=True),
        NavItem(NavLabels.SETTINGS, Icons.settings, bottom=True),
    ]

    return MainView(
        ui_context,
        items,
        view_factories,
        engine.ensure_pso_viewmodel()
    )


def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return SRC_DIR / relative


def run_app():
    app = create_app()
    splash = show_splash()

    # set the icon for Windows
    icon_path = resource_path("resources/icons/app.ico")

    app.setWindowIcon(QIcon(str(icon_path)))

    setup_logging(LOG_DIR, logging.DEBUG)
    setup_output_directory(TEMP_DIR)

    engine = create_engine()
    connect_shutdown(app, engine)

    ui_context = engine.ui_context

    view_factories = create_view_factories(engine, ui_context)
    main_view = create_main_view(engine, ui_context, view_factories)

    main_view.preload_views()

    main_view.show()
    splash.finish(main_view)

    QTimer.singleShot(750, lambda: engine.run_warmup(1))

    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
