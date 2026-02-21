from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QT_TRANSLATE_NOOP
import logging
from pathlib import Path
import sys

from app_engine import AppEngine
from viewmodels import PlotViewModel
from views import PlantView, PlotView, PlotConfiguration

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

    plant_view = PlantView(engine.lang_vm, engine.plant_vm)
    plant_view.show()

    plt_cfg = PlotConfiguration(
        context="plot.view",
        title=str(QT_TRANSLATE_NOOP("plot.view", "TestPlot")),
        x_label=str(QT_TRANSLATE_NOOP("plot.view", "X-Label")),
        y_label=str(QT_TRANSLATE_NOOP("plot.view", "Y-Label")),
        figsize=(5, 4)
    )
    vm = PlotViewModel()
    plot_view = PlotView(vm, plt_cfg, engine.lang_vm)

    vm.update_data("test", ([0, 1, 2, 3], [0, 1, 2, 3]))

    plot_view.show()

    sys.exit(app.exec())