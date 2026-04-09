from enum import StrEnum
from dataclasses import dataclass
from typing import Type
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QDoubleValidator, QValidator


@dataclass
class FieldConfig:
    key: str | FieldType
    widget_type: Type[QWidget] = QLabel
    create_label: bool = True
    validator: QValidator = QDoubleValidator()
    toggleable: bool = False
    toggle_default: bool = True

    def __len__(self) -> int:
        return 1


@dataclass
class SectionConfig:
    key: str | FieldType
    fields: list[FieldConfig | SectionConfig]
    columns: int = 2
    toggleable: bool = False

    def __post_init__(self):
        if self.columns % 2 != 0:
            raise ValueError(f"Columns {self.columns} must be even")

    def __len__(self) -> int:
        count = 0
        for f in self.fields:
            count += len(f)

        return count // (self.columns // 2) + 1


class FieldType(StrEnum):
    ...


# PlotViewModel / PlotWidget
class PlotField(FieldType):
    X_MIN = "x_min"
    X_MAX = "x_max"
    GRID = "grid"


# PlantViewModel / PlantView
class PlantField(FieldType):
    POLYNOM = "polynom"
    NUM = "num"
    DEN = "den"
    POLYNOM_FORMULA = "polynom_formula"

    BINOMINAL = "binomial"
    ZERO = "zero"
    POLE = "pole"
    BINOMINAL_FORMULA = "binomial_formula"


# ControllerViewModel / ControllerView
class ControllerField(FieldType):
    CONSTRAINT = "constraint"
    CONSTRAINT_MIN = "const_min"
    CONSTRAINT_MAX = "const_max"

    CONTROLLER_TYPE = "type"

    ANTI_WINDUP = "anti_wind"
    ANTI_WINDUP_METHODE = "anti_windup_method"
    FACTOR_KA = "ka"

    FILTER_TIME_CONSTANT = "filter_time_constant"
    TUNING_FACTOR = "tuning_factor"
    SAMPLING_RATE = "sampling_rate"

    BLOCK_DIAGRAM = "block_diagram"


# PsoConfigurationViewModel / PsoConfigurationView
class PsoField(FieldType):
    BLOCK_DIAGRAM = "block_diagram"

    PLANT = "plant"
    PLANT_TF = "plant_tf"

    EXCITATION = "excitation"
    EXCITATION_TARGET = "excitation_target"
    FUNCTION_FORMULA = "function_formula"

    SIMULATION_TIME = "simulation_time"
    T0 = "t0"
    T1 = "t1"

    PERFORMANCE_INDEX = "performance_index"
    TIME_DOMAIN = "time_domain"
    ERROR_CRITERION = "error_criterion"
    OVERSHOOT_CONTROL = "overshoot_control"
    SLEW_RATE_LIMITER = "slew_rate_limiter"
    SLEW_RATE_MAX = "slew_rate_max"
    SLEW_WINDOW_SIZE = "slew_window_size"
    FREQUENCY_DOMAIN = "frequency_domain"
    GAIN_MARGIN = "gain_margin"
    PHASE_MARGIN = "phase_margin"
    STABILITY_MARGIN = "stability_margin"

    PSO_BOUNDS = "pso_bounds"
    KP_BOUNDS = "kp_bounds"
    KP_MIN = "kp_min"
    KP_MAX = "kp_max"
    TI_BOUNDS = "ti_bounds"
    TI_MIN = "ti_min"
    TI_MAX = "ti_max"
    TD_BOUNDS = "td_bounds"
    TD_MIN = "td_min"
    TD_MAX = "td_max"

    RUN_PSO = "run_pso"
    INTERRUPT_PSO = "interrupt_pso"


# EvaluationViewModel / EvaluationView
class EvaluationField(FieldType):
    PLANT = "plant"
    TF_PLANT = "tf_plant"
    CONTROLLER = "controller"
    TF_CONTROLLER = "tf_controller"
    OPEN_LOOP = "open_loop"
    TF_OPEN_LOOP = "tf_open_loop"
    CLOSED_LOOP = "closed_loop"
    TF_CLOSED_LOOP = "tf_closed_loop"
    SENSITIVITY = "sensitivity"
    TF_SENSITIVITY = "tf_sensitivity"


# EvaluationViewModel / EvaluationView
class PsoResultField(FieldType):
    RUN_TIME = "run_time"
    TIME = "time"

    CONTROLLER_PARAMETERS = "controller_parameters"
    KP = "kp"
    TI = "ti"
    TD = "td"
    FILTER_TIME_CONSTANT = "filter_time_constant"
    TF = "tf"
    TF_LIMITED = "tf_limited"
    MIN_SAMPLING_RATE = "min_sampling_rate"

    PERFORMANCE_INDEX = "performance_index"

    TIME_DOMAIN = "time_domain"
    ERROR_CRITERION = "error_criterion"
    OVERSHOOT_CONTROL = "overshoot_control"
    SLEW_RATE = "slew_rate"

    FREQUENCY_DOMAIN = "frequency_domain"
    GAIN_MARGIN = "gain_margin"
    PHASE_MARGIN = "phase_margin"
    STABILITY_MARGIN = "stability_margin"


# DataManagementViewModel / DataManagementView
class DataManagementField(FieldType):
    EXPORT = "export"
    IMPORT = "import"
    REPORT = "report"


# SettingsViewModle / SettingsView
class SettingsField(FieldType):
    LANGUAGE = "language"
    THEME = "theme"

    PSO = "pso"
    PSO_ITERATIONS = "pso_iterations"
    PSO_PARTICLES = "pso_particles"

    SOLVER = "solver"
    SOLVER_TYPE = "solver_type"
    SOLVER_TIME_STEP = "solver_time_step"
