import logging

from models import PlantModel, SettingsModel, FunctionModel, PsoConfigurationModel
from viewmodels import PlantViewModel, LanguageViewModel, PlotViewModel, FunctionViewModel

class AppEngine:
    def __init__(self):

        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Start new Application")

        self.model_settings = SettingsModel()
        self.model_plant = PlantModel()
        self.model_function = FunctionModel()
        self.model_pso = PsoConfigurationModel()

        self.vm_lang = LanguageViewModel(self.model_settings)

        self.model_plant = PlantModel()

        self.model_function = FunctionModel()

        self.vm_plant = PlantViewModel(self.model_plant, self.model_settings)
        self.vm_plot_plant = PlotViewModel()
        self.vm_function = FunctionViewModel(self.model_function)
        self.vm_plot_function = PlotViewModel()
