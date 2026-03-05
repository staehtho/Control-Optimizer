from app_domain.functions import NullFunction
from models import PlantModel, SettingsModel, FunctionModel, PsoConfigurationModel, ControllerModel, SimulationModel


class ModelContainer:
    def __init__(self):
        self._model_functions: dict[str, FunctionModel] = {}

        self.model_settings = SettingsModel()
        self.model_plant = PlantModel()
        self.model_pso = PsoConfigurationModel()
        self.model_controller = ControllerModel()
        self.model_simulation = SimulationModel()

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
