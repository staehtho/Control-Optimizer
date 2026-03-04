import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from app_domain import AppEngine
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import FunctionTypes
from views import PlantView, FunctionView, ControllerView, PsoConfigurationView, EvaluationView, MainView, BaseView
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
    app.aboutToQuit.connect(engine.shutdown)
    ui_context = engine.ui_context
    BaseView.load_themes(ui_context.vm_theme.get_theme_cfg(), ui_context.vm_theme.current_theme)
    ui_context.vm_theme.themeChanged.connect(BaseView.set_theme)

    vm_function = engine.ensure_function_viewmodel("excitation_target")
    vm_function.set_selected_function(FunctionTypes.STEP)

    vm_functions = {title.name: engine.ensure_function_viewmodel(title.name) for title in ExcitationTarget}

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
            ui_context, engine.vm_plant, engine.vm_evaluator, vm_functions,
            engine.ensure_plot_viewmodel("response"), parent=parent
        )
    }

    main_view = MainView(ui_context, items, view_factories)
    main_view.show()

    sys.exit(app.exec())
