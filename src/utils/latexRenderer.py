import io
import matplotlib.pyplot as plt
import logging

from PySide6.QtGui import QPixmap, QPalette
from PySide6.QtWidgets import QApplication


class LatexRenderer:
    @staticmethod
    def latex_to_pixmap(text: str, font_size: int = 0) -> QPixmap:
        logger = logging.getLogger("matplotlib.font_manager")

        old_level = logger.level
        logger.setLevel(logging.CRITICAL + 1)  # nichts wird mehr geloggt

        app = QApplication.instance()

        # --- Farbe ---
        qt_color = app.palette().color(QPalette.Text)
        color = (
            qt_color.redF(),
            qt_color.greenF(),
            qt_color.blueF(),
        )

        # --- Qt Font & DPI ---
        font = app.font()
        if font_size == 0:
            qt_point_size = font.pointSizeF()
        else:
            qt_point_size = font_size

        screen = app.primaryScreen()
        logical_dpi = screen.logicalDotsPerInch() if screen else 96.0
        dpr = screen.devicePixelRatio() if screen else 1.0

        # --- DPI-korrigierte matplotlib-Schriftgrösse ---
        mpl_fontsize = qt_point_size * logical_dpi / 72.0

        # --- Figure ---
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_alpha(0)

        fig.text(
            0,
            0,
            f"${text}$",
            fontsize=mpl_fontsize,
            color=color,
            ha="left",
            va="bottom",
        )

        # --- Render ---
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=logical_dpi * dpr,
            bbox_inches="tight",
            pad_inches=0,
            transparent=True,
        )
        plt.close(fig)

        # --- Pixmap ---
        buf.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        pixmap.setDevicePixelRatio(dpr)

        logger.setLevel(old_level)

        return pixmap