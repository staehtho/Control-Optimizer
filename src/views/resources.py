from pathlib import Path
from dataclasses import dataclass

SRC_DIR = Path(__file__).parent.parent
RESOURCES_DIR = SRC_DIR / "resources"

# -------------------------------------------------
# Block Diagram
# -------------------------------------------------
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


# -------------------------------------------------
# Icons
# -------------------------------------------------
ICONS_DIR = RESOURCES_DIR / "icons"


@dataclass(frozen=True)
class Icons:
    control_optimizer: str = "control_optimizer.svg"
    controller: str = "controller.svg"
    evaluation: str = "evaluation.svg"
    excitation_function: str = "excitation_function.svg"
    menu: str = "menu.svg"
    plant: str = "plant.svg"
    pso_parameter: str = "pso_parameter.svg"
    settings: str = "settings.svg"
    simulation: str = "simulation.svg"

