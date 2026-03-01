import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from app_domain import AppEngine
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import FunctionTypes
from views import PlantView, FunctionView, ControllerView, PsoConfigurationView, EvaluationView, MainView
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
        if w.focusPolicy() != Qt.NoFocus
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

    for log in ("matplotlib.font_manager", "numba.core.ssa", "numba.core.byteflow", "numba.core.interpreter"):
        logger = logging.getLogger(log)
        old_level = logger.level
        logger.setLevel(logging.CRITICAL + 1)  # nichts wird mehr geloggt

    app = QApplication(sys.argv)

    engine = AppEngine()

    vm_function = engine.ensure_function_viewmodel("excitation_target")
    vm_function.set_selected_function(FunctionTypes.STEP)

    vm_functions = {title.name: engine.ensure_function_viewmodel(title.name) for title in ExcitationTarget}

    '''view_plant = PlantView(engine.vm_lang, engine.vm_plant, engine.ensure_plot_viewmodel("plant"))
    #print_tab_order(view_plant)
    view_plant.setWindowTitle(view_plant.__class__.__name__)
    view_plant.show()

    view_function = FunctionView(engine.vm_lang, engine.ensure_function_viewmodel("excitation_target"),
                                 engine.ensure_plot_viewmodel("function"))
    #print_tab_order(view_function)
    view_function.setWindowTitle(view_function.__class__.__name__)
    view_function.show()

    view_controller = ControllerView(engine.vm_lang, engine.vm_controller)
    ## print_tab_order(view_controller)
    view_controller.setWindowTitle(view_controller.__class__.__name__)
    view_controller.show()

    view_pso = PsoConfigurationView(engine.vm_lang, engine.vm_plant,
                                    engine.ensure_function_viewmodel("excitation_target"), engine.vm_pso)
    # print_tab_order(view_pso)
    view_pso.setWindowTitle(view_pso.__class__.__name__)
    view_pso.show()


    view_evaluator = EvaluationView(engine.vm_lang, engine.vm_plant, engine.vm_evaluator, vm_functions,
                                    engine.ensure_plot_viewmodel("response"))
    # print_tab_order(view_evaluator)
    view_evaluator.setWindowTitle(view_evaluator.__class__.__name__)
    view_evaluator.show()'''

    items = [NavItem(key, "") for key in NavLabels]

    view_factories = {
        NavLabels.PLANT: lambda parent=None: PlantView(
            engine.vm_lang, engine.vm_plant, engine.ensure_plot_viewmodel("plant"), parent=parent
        ),
        NavLabels.EXCITATION_FUNCTION: lambda parent=None: FunctionView(
            engine.vm_lang, engine.ensure_function_viewmodel("excitation_target"),
            engine.ensure_plot_viewmodel("function"), parent=parent
        ),
        NavLabels.CONTROLLER: lambda parent=None: ControllerView(
            engine.vm_lang, engine.vm_controller, parent=parent
        ),
        NavLabels.PSO_PARAMETER: lambda parent=None: PsoConfigurationView(
            engine.vm_lang, engine.vm_plant, engine.ensure_function_viewmodel("excitation_target"), engine.vm_pso,
            parent=parent
        ),
        NavLabels.EVALUATION: lambda parent=None: EvaluationView(
            engine.vm_lang, engine.vm_plant, engine.vm_evaluator, vm_functions,
            engine.ensure_plot_viewmodel("response"), parent=parent
        )
    }

    main_view = MainView(engine.vm_lang, items, view_factories)
    main_view.show()

    sys.exit(app.exec())