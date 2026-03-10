from enum import Enum


class FieldType(Enum):
    ...


# PlotViewModel / PlotWidget
class PlotField(FieldType):
    X_MIN = "x_min"
    X_MAX = "x_max"
    GRID = "grid"


# PlantViewModel / PlantView
class PlantField(FieldType):
    NUM = "num"
    DEN = "den"


# ControllerViewModel / ControllerView
class ControllerField(FieldType):
    CONSTRAINT = "constraint"
    CONSTRAINT_MIN = "const_min"
    CONSTRAINT_MAX = "const_max"

    CONTROLLER_TYPE = "type"

    ANTI_WINDUP = "anti_wind"


# PsoConfigurationViewModel / PsoConfigurationView
class PsoField(FieldType):
    EXCITATION_TARGET = "excitation_target"
    FUNCTION_FORMULA = "function_formula"

    SIMULATION_TIME = "simulation_time"
    T0 = "t0"
    T1 = "t1"

    PERFORMANCE_INDEX = "performance_index"
    TIME_DOMAIN = "time_domain"

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
