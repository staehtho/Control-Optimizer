from __future__ import annotations

from typing import TYPE_CHECKING

from app_domain.controlsys import AntiWindup, ExcitationTarget, MySolver, PerformanceIndex
from app_domain.functions import FunctionTypes, resolve_function_type

if TYPE_CHECKING:
    from .function_model import FunctionModel
    from .model_container import ModelContainer


def export_project_state(container: ModelContainer) -> dict:
    return {
        "version": 1,
        "plant": {
            "num": list(container.model_plant.num),
            "den": list(container.model_plant.den),
        },
        "controller": {
            "controller_type": container.model_controller.controller_type,
            "constraint_min": container.model_controller.constraint_min,
            "constraint_max": container.model_controller.constraint_max,
            "anti_windup": container.model_controller.anti_windup.name,
            "ka": container.model_controller.ka,
            "ka_enabled": container.model_controller.ka_enabled,
            "tuning_factor": container.model_controller.tuning_factor,
            "sampling_rate": container.model_controller.sampling_rate,
        },
        "pso": {
            "t0": container.model_pso.t0,
            "t1": container.model_pso.t1,
            "excitation_target": container.model_pso.excitation_target.name,
            "kp_min": container.model_pso.kp_min,
            "kp_max": container.model_pso.kp_max,
            "ti_min": container.model_pso.ti_min,
            "ti_max": container.model_pso.ti_max,
            "td_min": container.model_pso.td_min,
            "td_max": container.model_pso.td_max,
            "error_criterion": container.model_pso.error_criterion.name,
            "overshoot_control": container.model_pso.overshoot_control,
            "overshoot_control_enabled": container.model_pso.overshoot_control_enabled,
            "slew_rate_max": container.model_pso.slew_rate_max,
            "slew_window_size": container.model_pso.slew_window_size,
            "slew_rate_limit_enabled": container.model_pso.slew_rate_limit_enabled,
            "gain_margin": container.model_pso.gain_margin,
            "gain_margin_enabled": container.model_pso.gain_margin_enabled,
            "phase_margin": container.model_pso.phase_margin,
            "phase_margin_enabled": container.model_pso.phase_margin_enabled,
            "stability_margin": container.model_pso.stability_margin,
            "stability_margin_enabled": container.model_pso.stability_margin_enabled,
        },
        "settings": {
            "solver": container.model_settings.solver.name,
            "time_step": container.model_settings.time_step,
            "pso_swarm_size": container.model_settings.pso_swarm_size,
            "pso_repeat_runs": container.model_settings.pso_repeat_runs,
            "pso_randomness": container.model_settings.pso_randomness,
            "pso_u1": container.model_settings.pso_u1,
            "pso_u2": container.model_settings.pso_u2,
            "pso_initial_range": [
                container.model_settings.pso_initial_range_start,
                container.model_settings.pso_initial_range_end
            ],
            "pso_initial_swarm_span": container.model_settings.pso_initial_swarm_span,
            "pso_min_neighbors_fraction": container.model_settings.pso_min_neighbors_fraction,
            "pso_max_stall": container.model_settings.pso_max_stall,
            "pso_max_iter": container.model_settings.pso_max_iter,
            "pso_stall_windows_required": container.model_settings.pso_stall_windows_required,
            "pso_space_factor": container.model_settings.pso_space_factor,
            "pso_convergence_factor": container.model_settings.pso_convergence_factor,
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
    plant = state.get("plant", {})
    if plant:
        container.model_plant.num = [float(value) for value in plant.get("num", container.model_plant.num)]
        container.model_plant.den = [float(value) for value in plant.get("den", container.model_plant.den)]

    controller = state.get("controller", {})
    if controller:
        container.model_controller.controller_type = controller.get(
            "controller_type",
            container.model_controller.controller_type,
        )
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
        container.model_pso.kp_min = float(pso.get("kp_min", container.model_pso.kp_min))
        container.model_pso.kp_max = float(pso.get("kp_max", container.model_pso.kp_max))
        container.model_pso.ti_min = float(pso.get("ti_min", container.model_pso.ti_min))
        container.model_pso.ti_max = float(pso.get("ti_max", container.model_pso.ti_max))
        container.model_pso.td_min = float(pso.get("td_min", container.model_pso.td_min))
        container.model_pso.td_max = float(pso.get("td_max", container.model_pso.td_max))
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
