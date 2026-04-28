from __future__ import annotations

from app_domain.functions import NullFunction
from app_domain.controlsys import ControllerType
from app_types import CONTROLLER_SPECS

from .controller_model import ControllerModel
from .data_management_model import DataManagementModel
from .function_model import FunctionModel
from .plant_model import PlantModel
from .project_state_io import export_project_state, import_project_bounds, import_project_state
from .pso_configuration_model import PsoConfigurationModel
from .settings_model import SettingsModel
from .simulation_model import SimulationModel


class ModelContainer:
    def __init__(self):
        self._model_functions: dict[str, FunctionModel] = {}

        self.model_settings = SettingsModel()
        self.model_plant = PlantModel()

        controller_type = ControllerType.PID
        default_controller_spec = CONTROLLER_SPECS[controller_type]()
        self.model_controller = ControllerModel(
            controller_type=controller_type,
            controller_spec=default_controller_spec
        )

        lw, up = default_controller_spec.bounds
        params = default_controller_spec.param_names
        self.model_pso = PsoConfigurationModel(
            min_bounds={k: v for k, v in zip(params, default_controller_spec.min_bounds)},
            lower_bounds={k: v for k, v in zip(params, lw)},
            upper_bounds={k: v for k, v in zip(params, up)},
            n_params=len(lw)
        )

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

    @property
    def model_functions(self):
        return self._model_functions

    def export_project_state(self) -> dict:
        return export_project_state(self)

    def import_project_state(self, state: dict) -> None:
        import_project_state(self, state)

    def import_project_bounds(self, state: dict) -> None:
        import_project_bounds(self, state)
