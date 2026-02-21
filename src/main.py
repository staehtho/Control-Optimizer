from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
import logging
from pathlib import Path
import sys

from app_engine import AppEngine
from views import PlantView


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

    plant_view = PlantView(engine.vm_lang, engine.vm_plant, engine.vm_plot_plant)
    print_tab_order(plant_view)
    plant_view.show()

    sys.exit(app.exec())