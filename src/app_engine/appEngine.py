import logging

from models import PlantModel, SettingsModel
from viewmodels import PlantViewModel, LanguageViewModel

class AppEngine:
    def __init__(self):

        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Start new Application")

        self.settings_model = SettingsModel()
        self.lang_vm = LanguageViewModel(self.settings_model)

        self.plant_model = PlantModel(solver=self.settings_model.get_solver())

        self.plant_vm = PlantViewModel(self.plant_model)
