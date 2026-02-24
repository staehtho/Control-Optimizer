import logging

from models import ModelContainer
from service import SimulationService
from viewmodels import PlantViewModel, LanguageViewModel, PlotViewModel, FunctionViewModel


class AppEngine:
    def __init__(self):

        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Start new Application")

        self.simulation_service = SimulationService()

        self.model_container = ModelContainer()

        self.vm_lang = LanguageViewModel(self.model_container.model_settings)
        self.vm_plot_plant = PlotViewModel()
        self.vm_plant = PlantViewModel(self.model_container, self.simulation_service)
        self.vm_plot_function = PlotViewModel()
        self.vm_function = FunctionViewModel(self.model_container.model_function, self.simulation_service)
