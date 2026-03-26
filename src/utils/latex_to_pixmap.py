import io
import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from PySide6.QtGui import QPixmap, QPalette, QColor
from PySide6.QtWidgets import QApplication


def latex_to_pixmap(text: str, font_size: int = 0, font_size_scale: float = 1.0) -> QPixmap:
    logger = logging.getLogger("matplotlib.font_manager")

    old_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)  # nichts wird mehr geloggt

    app = QApplication.instance()

    # --- Color from active app theme (derived from QSS) ---
    theme_text_color = app.property("themeTextColor")
    if not isinstance(theme_text_color, QColor) or not theme_text_color.isValid():
        theme_text_color = app.palette().color(QPalette.Text)
    color = (
        theme_text_color.redF(),
        theme_text_color.greenF(),
        theme_text_color.blueF(),
    )

    # --- Qt Font & DPI ---
    font = app.font()
    if font_size == 0:
        qt_point_size = font.pointSizeF()
    else:
        qt_point_size = font_size

    # scale font size
    qt_point_size *= font_size_scale

    screen = app.primaryScreen()
    logical_dpi = screen.logicalDotsPerInch() if screen else 96.0
    dpr = screen.devicePixelRatio() if screen else 1.0

    # --- DPI-korrigierte matplotlib-Schriftgrösse ---
    mpl_fontsize = qt_point_size * logical_dpi / 72.0

    # --- Figure (off-screen Agg canvas; avoids transient Qt windows) ---
    fig = Figure(figsize=(0.01, 0.01))
    canvas = FigureCanvasAgg(fig)
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
    canvas.draw()

    # --- Pixmap ---
    buf.seek(0)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.read())
    pixmap.setDevicePixelRatio(dpr)

    logger.setLevel(old_level)

    return pixmap
