import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from app_domain import AppEngine
from views import PlantView, FunctionView


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

    logger = logging.getLogger("matplotlib.font_manager")

    old_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)  # nichts wird mehr geloggt

    app = QApplication(sys.argv)

    engine = AppEngine()

    view_plant = PlantView(engine.vm_lang, engine.vm_plant, engine.vm_plot_plant)
    #print_tab_order(view_plant)
    view_plant.show()

    view_function = FunctionView(engine.vm_lang, engine.vm_function, engine.vm_plot_function)
    #print_tab_order(view_function)
    view_function.show()

    sys.exit(app.exec())