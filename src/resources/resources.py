import os
import sys
from pathlib import Path
from dataclasses import dataclass


# ============================================================
# Helper: detect if running as PyInstaller EXE
# ============================================================

def is_frozen():
    return hasattr(sys, "_MEIPASS")


# ============================================================
# Base directories
# ============================================================

# Development mode → project root
DEV_SRC_DIR = Path(__file__).parent.parent

# Frozen mode → PyInstaller _MEIPASS root
if is_frozen():
    SRC_DIR = Path(sys._MEIPASS)
else:
    SRC_DIR = DEV_SRC_DIR

RESOURCES_DIR = SRC_DIR / "resources"


# ============================================================
# User-writable directories (only used when frozen)
# ============================================================

def get_user_data_dir():
    base = Path(os.getenv("LOCALAPPDATA")) / "Control_Optimizer"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_temp_dir():
    if is_frozen():
        d = get_user_data_dir() / "temp"
    else:
        d = RESOURCES_DIR / "temp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_log_dir():
    if is_frozen():
        d = get_user_data_dir() / "logs"
    else:
        d = SRC_DIR / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_settings_dir():
    if is_frozen():
        d = get_user_data_dir() / "settings"
    else:
        d = SRC_DIR / "settings"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ============================================================
# Public paths used by the rest of the app
# ============================================================

TEMP_DIR = get_temp_dir()
LOG_DIR = get_log_dir()

CONFIG_DIR = SRC_DIR / "config"
THEMES_DIR = CONFIG_DIR / "themes"
I18N_DIR = SRC_DIR / "i18n"
SETTINGS_DIR = get_settings_dir()


# ============================================================
# Block Diagram
# ============================================================

BLOCK_DIAGRAM_DIR = RESOURCES_DIR / "block_diagram"


@dataclass(frozen=True)
class BlockDiagram:
    blank_base: str = "blank_base.svg"
    controller_in: str = "controller_in.svg"
    controller_out: str = "controller_out.svg"
    p_path: str = "p_path.svg"
    d_path: str = "d_path.svg"
    i_path: str = "i_path.svg"

    closed_loop: str = "closed_loop.svg"

    backcalculation: str = "backcalculation.svg"
    clamping: str = "clamping.svg"
    conditional: str = "conditional.svg"


# ============================================================
# Icons
# ============================================================

ICONS_DIR = RESOURCES_DIR / "icons"


@dataclass(frozen=True)
class Icons:
    control_optimizer: str = "control_optimizer.svg"
    controller: str = "controller.svg"
    data_management: str = "data_management.svg"
    evaluation: str = "evaluation.svg"
    excitation_function: str = "excitation_function.svg"
    menu: str = "menu.svg"
    nav_next: str = "nav_next.svg"
    nav_previous: str = "nav_previous.svg"
    plant: str = "plant.svg"
    pso_parameter: str = "pso_parameter.svg"
    settings: str = "settings.svg"
    simulation: str = "simulation.svg"


# ============================================================
# Output files
# ============================================================

@dataclass(frozen=True)
class OutputFiles:
    block_diagram: str = "block_diagram.svg"
    time_domain_plot: str = "time_domain_plot.svg"
    bode_plot: str = "bode_plot.svg"
