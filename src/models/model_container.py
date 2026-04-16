from __future__ import annotations

from app_domain.controlsys import AntiWindup, ExcitationTarget, MySolver, PerformanceIndex
from app_domain.functions import FunctionTypes, NullFunction, resolve_function_type
from models import PlantModel, SettingsModel, FunctionModel, PsoConfigurationModel, ControllerModel, SimulationModel
from app_domain.functions import NullFunction
from models import (
    PlantModel, SettingsModel, FunctionModel, PsoConfigurationModel, ControllerModel, SimulationModel,
    DataManagementModel
)


class ModelContainer:
    def __init__(self):
        self._model_functions: dict[str, FunctionModel] = {}

        self.model_settings = SettingsModel()
        self.model_plant = PlantModel()
        self.model_pso = PsoConfigurationModel()
        self.model_controller = ControllerModel()
        self.model_simulation = SimulationModel()
        self.model_data = DataManagementModel()

    def ensure_function_model(self, key: str) -> FunctionModel:
        """
        Ensure a FunctionModel exists for the given key, creating and caching it if necessary.

        Implements a lazy-initializing factory with caching:
        - Returns the existing FunctionModel if present.
        - Otherwise, creates, caches, and returns a new FunctionModel.

        Args:
            key (str): Identifier for the function (e.g., "plant", "function").

        Returns:
            FunctionModel: The cached or newly created FunctionModel instance.
        """
        return self._model_functions.setdefault(key, FunctionModel(NullFunction()))

    def export_project_state(self) -> dict:
        return {
            "version": 1,
            "plant": {
                "num": list(self.model_plant.num),
                "den": list(self.model_plant.den),
            },
            "controller": {
                "controller_type": self.model_controller.controller_type,
                "constraint_min": self.model_controller.constraint_min,
                "constraint_max": self.model_controller.constraint_max,
                "anti_windup": self.model_controller.anti_windup.name,
                "ka": self.model_controller.ka,
                "ka_enabled": self.model_controller.ka_enabled,
                "tuning_factor": self.model_controller.tuning_factor,
                "sampling_rate": self.model_controller.sampling_rate,
            },
            "pso": {
                "t0": self.model_pso.t0,
                "t1": self.model_pso.t1,
                "excitation_target": self.model_pso.excitation_target.name,
                "kp_min": self.model_pso.kp_min,
                "kp_max": self.model_pso.kp_max,
                "ti_min": self.model_pso.ti_min,
                "ti_max": self.model_pso.ti_max,
                "td_min": self.model_pso.td_min,
                "td_max": self.model_pso.td_max,
                "error_criterion": self.model_pso.error_criterion.name,
                "overshoot_control": self.model_pso.overshoot_control,
                "overshoot_control_enabled": self.model_pso.overshoot_control_enabled,
                "slew_rate_max": self.model_pso.slew_rate_max,
                "slew_window_size": self.model_pso.slew_window_size,
                "slew_rate_limit_enabled": self.model_pso.slew_rate_limit_enabled,
                "gain_margin": self.model_pso.gain_margin,
                "gain_margin_enabled": self.model_pso.gain_margin_enabled,
                "phase_margin": self.model_pso.phase_margin,
                "phase_margin_enabled": self.model_pso.phase_margin_enabled,
                "stability_margin": self.model_pso.stability_margin,
                "stability_margin_enabled": self.model_pso.stability_margin_enabled,
            },
            "settings": {
                "solver": self.model_settings.get_solver().name,
                "time_step": self.model_settings.get_time_step(),
                "pso_particle": self.model_settings.get_pso_particle(),
                "pso_iterations": self.model_settings.get_pso_iterations(),
            },
            "functions": (
                {
                    "excitation_target": self._export_function_model(
                        self._model_functions["excitation_target"]
                    )
                }
                if "excitation_target" in self._model_functions
                else {}
            ),
        }

    def import_project_state(self, state: dict) -> None:
        plant = state.get("plant", {})
        if plant:
            self.model_plant.num = [float(value) for value in plant.get("num", self.model_plant.num)]
            self.model_plant.den = [float(value) for value in plant.get("den", self.model_plant.den)]

        controller = state.get("controller", {})
        if controller:
            self.model_controller.controller_type = controller.get(
                "controller_type",
                self.model_controller.controller_type,
            )
            self.model_controller.constraint_min = float(
                controller.get("constraint_min", self.model_controller.constraint_min)
            )
            self.model_controller.constraint_max = float(
                controller.get("constraint_max", self.model_controller.constraint_max)
            )
            anti_windup = controller.get("anti_windup")
            if anti_windup is not None:
                self.model_controller.anti_windup = AntiWindup[anti_windup]
            self.model_controller.ka = float(controller.get("ka", self.model_controller.ka))
            self.model_controller.ka_enabled = bool(
                controller.get("ka_enabled", self.model_controller.ka_enabled)
            )
            self.model_controller.tuning_factor = float(
                controller.get("tuning_factor", self.model_controller.tuning_factor)
            )
            sampling_rate = controller.get("sampling_rate", self.model_controller.sampling_rate)
            self.model_controller.sampling_rate = None if sampling_rate is None else float(sampling_rate)

        pso = state.get("pso", {})
        if pso:
            self.model_pso.t0 = float(pso.get("t0", self.model_pso.t0))
            self.model_pso.t1 = float(pso.get("t1", self.model_pso.t1))
            excitation_target = pso.get("excitation_target")
            if excitation_target is not None:
                self.model_pso.excitation_target = ExcitationTarget[excitation_target]
            self.model_pso.kp_min = float(pso.get("kp_min", self.model_pso.kp_min))
            self.model_pso.kp_max = float(pso.get("kp_max", self.model_pso.kp_max))
            self.model_pso.ti_min = float(pso.get("ti_min", self.model_pso.ti_min))
            self.model_pso.ti_max = float(pso.get("ti_max", self.model_pso.ti_max))
            self.model_pso.td_min = float(pso.get("td_min", self.model_pso.td_min))
            self.model_pso.td_max = float(pso.get("td_max", self.model_pso.td_max))
            error_criterion = pso.get("error_criterion")
            if error_criterion is not None:
                self.model_pso.error_criterion = PerformanceIndex[error_criterion]
            self.model_pso.overshoot_control = float(
                pso.get("overshoot_control", self.model_pso.overshoot_control)
            )
            self.model_pso.overshoot_control_enabled = bool(
                pso.get("overshoot_control_enabled", self.model_pso.overshoot_control_enabled)
            )
            self.model_pso.slew_rate_max = float(
                pso.get("slew_rate_max", self.model_pso.slew_rate_max)
            )
            self.model_pso.slew_window_size = int(
                pso.get("slew_window_size", self.model_pso.slew_window_size)
            )
            self.model_pso.slew_rate_limit_enabled = bool(
                pso.get("slew_rate_limit_enabled", self.model_pso.slew_rate_limit_enabled)
            )
            self.model_pso.gain_margin = float(pso.get("gain_margin", self.model_pso.gain_margin))
            self.model_pso.gain_margin_enabled = bool(
                pso.get("gain_margin_enabled", self.model_pso.gain_margin_enabled)
            )
            self.model_pso.phase_margin = float(pso.get("phase_margin", self.model_pso.phase_margin))
            self.model_pso.phase_margin_enabled = bool(
                pso.get("phase_margin_enabled", self.model_pso.phase_margin_enabled)
            )
            self.model_pso.stability_margin = float(
                pso.get("stability_margin", self.model_pso.stability_margin)
            )
            self.model_pso.stability_margin_enabled = bool(
                pso.get("stability_margin_enabled", self.model_pso.stability_margin_enabled)
            )

        settings = state.get("settings", {})
        if settings:
            solver = settings.get("solver", "")
            if solver is not None:
                self.model_settings.set_solver(MySolver[solver])
            if "time_step" in settings:
                self.model_settings.set_time_step(float(settings["time_step"]))
            if "pso_particle" in settings:
                self.model_settings.set_pso_particle(int(settings["pso_particle"]))
            if "pso_iterations" in settings:
                self.model_settings.set_pso_iterations(int(settings["pso_iterations"]))

        for key, function_state in state.get("functions", {}).items():
            self._import_function_model(key, function_state)

    @staticmethod
    def _export_function_model(model: FunctionModel) -> dict:
        function_type = resolve_function_type(model.selected_function)
        return {
            "type": function_type.name,
            "params": dict(model.selected_function.get_param()),
        }

    def _import_function_model(self, key: str, state: dict) -> None:
        type_name = state.get("type")
        if type_name is None:
            return

        function_type = FunctionTypes[type_name]
        model = self.ensure_function_model(key)
        model.selected_function = function_type.value()

        params = state.get("params", {})
        for param_key, param_value in params.items():
            model.selected_function.update_param_value(param_key, float(param_value))
