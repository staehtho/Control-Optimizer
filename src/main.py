from PySide6.QtWidgets import QApplication
import logging
from pathlib import Path
import sys

from app_engine import AppEngine
from views import PlantView

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
    plant_view.show()

    sys.exit(app.exec())