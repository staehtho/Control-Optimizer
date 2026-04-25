from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication

from app_domain.controlsys import AntiWindup, ControllerType, ExcitationTarget, MySolver, PerformanceIndex
from app_domain.functions import FunctionTypes, resolve_function_type
from app_types import CONTROLLER_SPECS

if TYPE_CHECKING:
    from .function_model import FunctionModel
    from .model_container import ModelContainer

PROJECT_STATE_VERSION = 1.1
SUPPORTED_PROJECT_STATE_VERSIONS = {1.1}


def export_project_state(container: ModelContainer) -> dict:
    controller = container.model_controller
    pso = container.model_pso
    settings = container.model_settings

    return {
        "version": PROJECT_STATE_VERSION,
        "plant": {
            "num": list(container.model_plant.num),
            "den": list(container.model_plant.den),
        },
        "controller": {
            "controller_type": controller.controller_type.name,
            "constraint_min": controller.constraint_min,
            "constraint_max": controller.constraint_max,
            "anti_windup": controller.anti_windup.name,
            "ka": controller.ka,
            "ka_enabled": controller.ka_enabled,
            "tuning_factor": controller.tuning_factor,
            "sampling_rate": controller.sampling_rate,
        },
        "pso": {
            "t0": pso.t0,
            "t1": pso.t1,
            "excitation_target": pso.excitation_target.name,
            "lower_bounds": {key: float(value) for key, value in pso.lower_bounds.items()},
            "upper_bounds": {key: float(value) for key, value in pso.upper_bounds.items()},
            "error_criterion": pso.error_criterion.name,
            "overshoot_control": pso.overshoot_control,
            "overshoot_control_enabled": pso.overshoot_control_enabled,
            "slew_rate_max": pso.slew_rate_max,
            "slew_window_size": pso.slew_window_size,
            "slew_rate_limit_enabled": pso.slew_rate_limit_enabled,
            "gain_margin": pso.gain_margin,
            "gain_margin_enabled": pso.gain_margin_enabled,
            "phase_margin": pso.phase_margin,
            "phase_margin_enabled": pso.phase_margin_enabled,
            "stability_margin": pso.stability_margin,
            "stability_margin_enabled": pso.stability_margin_enabled,
        },
        "settings": {
            "solver": settings.solver.name,
            "time_step": settings.time_step,
            "pso_swarm_size": settings.pso_swarm_size,
            "pso_repeat_runs": settings.pso_repeat_runs,
            "pso_randomness": settings.pso_randomness,
            "pso_u1": settings.pso_u1,
            "pso_u2": settings.pso_u2,
            "pso_initial_range": [
                settings.pso_initial_range_start,
                settings.pso_initial_range_end
            ],
            "pso_initial_swarm_span": settings.pso_initial_swarm_span,
            "pso_min_neighbors_fraction": settings.pso_min_neighbors_fraction,
            "pso_max_stall": settings.pso_max_stall,
            "pso_max_iter": settings.pso_max_iter,
            "pso_stall_windows_required": settings.pso_stall_windows_required,
            "pso_space_factor": settings.pso_space_factor,
            "pso_convergence_factor": settings.pso_convergence_factor,
        },
        "functions": (
            {
                "excitation_target": _export_function_model(
                    container.model_functions["excitation_target"]
                )
            }
            if "excitation_target" in container.model_functions
            else {}
        ),
    }


def import_project_state(container: ModelContainer, state: dict) -> None:
    try:
        if not isinstance(state, dict):
            raise ValueError(
                QCoreApplication.translate("ImportExport", "Project file must contain a JSON object at the top level"))

        version = state.get("version")
        if version is None:
            raise ValueError(
                QCoreApplication.translate("ImportExport", "Project file is missing the required 'version' field"))
        if version not in SUPPORTED_PROJECT_STATE_VERSIONS:
            supported = ", ".join(str(v) for v in sorted(SUPPORTED_PROJECT_STATE_VERSIONS))
            raise ValueError(QCoreApplication.translate("ImportExport",
                                                        "Unsupported project file version: {version}. Supported versions: {supported}").format(
                version=version, supported=supported))

        plant = state.get("plant", {})
        if plant:
            container.model_plant.num = [float(value) for value in plant.get("num", container.model_plant.num)]
            container.model_plant.den = [float(value) for value in plant.get("den", container.model_plant.den)]

        controller = state.get("controller", {})
        if controller:
            controller_type = _parse_enum(
                ControllerType,
                controller.get("controller_type", container.model_controller.controller_type),
            )
            container.model_controller.controller_type = controller_type
            container.model_controller.controller_spec = CONTROLLER_SPECS[controller_type]()
            container.model_controller.constraint_min = float(
                controller.get("constraint_min", container.model_controller.constraint_min)
            )
            container.model_controller.constraint_max = float(
                controller.get("constraint_max", container.model_controller.constraint_max)
            )
            anti_windup = controller.get("anti_windup", "")
            if anti_windup:
                container.model_controller.anti_windup = AntiWindup[anti_windup]
            container.model_controller.ka = float(controller.get("ka", container.model_controller.ka))
            container.model_controller.ka_enabled = bool(
                controller.get("ka_enabled", container.model_controller.ka_enabled)
            )
            container.model_controller.tuning_factor = float(
                controller.get("tuning_factor", container.model_controller.tuning_factor)
            )
            sampling_rate = controller.get("sampling_rate", container.model_controller.sampling_rate)
            container.model_controller.sampling_rate = None if sampling_rate is None else float(sampling_rate)

        pso = state.get("pso", {})
        if pso:
            container.model_pso.t0 = float(pso.get("t0", container.model_pso.t0))
            container.model_pso.t1 = float(pso.get("t1", container.model_pso.t1))
            excitation_target = pso.get("excitation_target", "")
            if excitation_target:
                container.model_pso.excitation_target = ExcitationTarget[excitation_target]
            error_criterion = pso.get("error_criterion", "")
            if error_criterion:
                container.model_pso.error_criterion = PerformanceIndex[error_criterion]
            container.model_pso.overshoot_control = float(
                pso.get("overshoot_control", container.model_pso.overshoot_control)
            )
            container.model_pso.overshoot_control_enabled = bool(
                pso.get("overshoot_control_enabled", container.model_pso.overshoot_control_enabled)
            )
            container.model_pso.slew_rate_max = float(
                pso.get("slew_rate_max", container.model_pso.slew_rate_max)
            )
            container.model_pso.slew_window_size = int(
                pso.get("slew_window_size", container.model_pso.slew_window_size)
            )
            container.model_pso.slew_rate_limit_enabled = bool(
                pso.get("slew_rate_limit_enabled", container.model_pso.slew_rate_limit_enabled)
            )
            container.model_pso.gain_margin = float(
                pso.get("gain_margin", container.model_pso.gain_margin)
            )
            container.model_pso.gain_margin_enabled = bool(
                pso.get("gain_margin_enabled", container.model_pso.gain_margin_enabled)
            )
            container.model_pso.phase_margin = float(
                pso.get("phase_margin", container.model_pso.phase_margin)
            )
            container.model_pso.phase_margin_enabled = bool(
                pso.get("phase_margin_enabled", container.model_pso.phase_margin_enabled)
            )
            container.model_pso.stability_margin = float(
                pso.get("stability_margin", container.model_pso.stability_margin)
            )
            container.model_pso.stability_margin_enabled = bool(
                pso.get("stability_margin_enabled", container.model_pso.stability_margin_enabled)
            )

        settings = state.get("settings", {})
        if settings:
            solver = settings.get("solver", "")
            if solver:
                container.model_settings.solver = MySolver[solver]
            if "time_step" in settings:
                container.model_settings.time_step = float(settings["time_step"])
            if "pso_swarm_size" in settings:
                container.model_settings.pso_swarm_size = int(settings["pso_swarm_size"])
            if "pso_repeat_runs" in settings:
                container.model_settings.pso_repeat_runs = int(settings["pso_repeat_runs"])
            if "pso_randomness" in settings:
                container.model_settings.pso_randomness = float(settings["pso_randomness"])
            if "pso_u1" in settings:
                container.model_settings.pso_u1 = float(settings["pso_u1"])
            if "pso_u2" in settings:
                container.model_settings.pso_u2 = float(settings["pso_u2"])
            if "pso_initial_range" in settings:
                initial_range = settings["pso_initial_range"]
                if isinstance(initial_range, (list, tuple)) and len(initial_range) >= 2:
                    container.model_settings.pso_initial_range_start = float(initial_range[0])
                    container.model_settings.pso_initial_range_end = float(initial_range[1])
            if "pso_initial_range_start" in settings:
                container.model_settings.pso_initial_range_start = float(settings["pso_initial_range_start"])
            if "pso_initial_range_end" in settings:
                container.model_settings.pso_initial_range_end = float(settings["pso_initial_range_end"])
            if "pso_initial_swarm_span" in settings:
                container.model_settings.pso_initial_swarm_span = int(settings["pso_initial_swarm_span"])
            if "pso_min_neighbors_fraction" in settings:
                container.model_settings.pso_min_neighbors_fraction = float(settings["pso_min_neighbors_fraction"])
            if "pso_max_stall" in settings:
                container.model_settings.pso_max_stall = int(settings["pso_max_stall"])
            if "pso_max_iter" in settings:
                container.model_settings.pso_max_iter = int(settings["pso_max_iter"])
            if "pso_stall_windows_required" in settings:
                container.model_settings.pso_stall_windows_required = int(settings["pso_stall_windows_required"])
            if "pso_space_factor" in settings:
                container.model_settings.pso_space_factor = float(settings["pso_space_factor"])
            if "pso_convergence_factor" in settings:
                container.model_settings.pso_convergence_factor = float(settings["pso_convergence_factor"])

        for key, function_state in state.get("functions", {}).items():
            _import_function_model(container, key, function_state)
    except KeyError as exc:
        raise ValueError(
            QCoreApplication.translate("ImportExport", "Unknown import field or enum value: {name}").format(
                name=exc.args[0])) from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(QCoreApplication.translate("ImportExport", "Invalid project file data: {message}").format(
            message=exc)) from exc


def import_project_bounds(container: ModelContainer, state: dict) -> None:
    try:
        if not isinstance(state, dict):
            raise ValueError(
                QCoreApplication.translate("ImportExport", "Project file must contain a JSON object at the top level"))

        pso = state.get("pso", {})
        if pso:
            _import_pso_bounds(container, pso)
    except KeyError as exc:
        raise ValueError(
            QCoreApplication.translate("ImportExport", "Unknown import field or enum value: {name}").format(
                name=exc.args[0])) from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(QCoreApplication.translate("ImportExport", "Invalid project file data: {message}").format(
            message=exc)) from exc


def _export_function_model(model: FunctionModel) -> dict:
    function_type = resolve_function_type(model.selected_function)
    return {
        "type": function_type.name,
        "params": dict(model.selected_function.get_param()),
    }


def _import_function_model(container: ModelContainer, key: str, state: dict) -> None:
    type_name = state.get("type", "")
    if not type_name:
        return

    function_type = FunctionTypes[type_name]
    model = container.ensure_function_model(key)
    model.selected_function = function_type.value()

    params = state.get("params", {})
    for param_key, param_value in params.items():
        model.selected_function.update_param_value(param_key, float(param_value))


def _parse_enum(enum_type: type, value):
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        return enum_type[value]
    return enum_type(value)


def _import_pso_bounds(container: ModelContainer, pso_state: dict) -> None:
    spec = container.model_controller.controller_spec
    param_names = list(spec.param_names)

    default_min = {key: float(value) for key, value in zip(param_names, spec.min_bounds)}
    default_lower = {key: float(value) for key, value in zip(param_names, spec.bounds[0])}
    default_upper = {key: float(value) for key, value in zip(param_names, spec.bounds[1])}

    lower_bounds, has_lower_bounds = _read_bounds_map(pso_state.get("lower_bounds"), default_lower)
    upper_bounds, has_upper_bounds = _read_bounds_map(pso_state.get("upper_bounds"), default_upper)

    container.model_pso.min_bounds = {key: default_min[key] for key in param_names}
    container.model_pso.lower_bounds = {key: lower_bounds.get(key, default_lower[key]) for key in param_names}
    container.model_pso.upper_bounds = {key: upper_bounds.get(key, default_upper[key]) for key in param_names}
    container.model_pso.n_params = int(pso_state.get("n_params", len(param_names)))


def _read_bounds_map(raw_bounds: dict | None, defaults: dict[str, float]) -> tuple[dict[str, float], bool]:
    if raw_bounds is None:
        return dict(defaults), False
    return ({
                key: float(raw_bounds.get(key, defaults[key]))
                for key in defaults
            }, True)
