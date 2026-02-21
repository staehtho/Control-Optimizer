import logging

from models import PlantModel, SettingsModel
from viewmodels import PlantViewModel, LanguageViewModel, PlotViewModel

class AppEngine:
    def __init__(self):

        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Start new Application")

        self.model_settings = SettingsModel()
        self.vm_lang = LanguageViewModel(self.model_settings)

        self.model_plant = PlantModel()

        self.vm_plant = PlantViewModel(self.model_plant, self.model_settings)
        self.vm_plot_plant = PlotViewModel()
