from app_domain.functions import StepFunction
from models import PlantModel, SettingsModel, FunctionModel, PsoConfigurationModel, ControllerModel

class ModelContainer:
    def __init__(self):

        self.model_settings = SettingsModel()
        self.model_plant = PlantModel()
        self.model_function = FunctionModel(StepFunction())
        self.model_pso = PsoConfigurationModel()
        self.model_controller = ControllerModel()
