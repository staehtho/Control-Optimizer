import logging
import numpy as np

from app_domain import PsoSimulationParam
from app_domain.controlsys import MySolver, AntiWindup, ExcitationTarget, PerformanceIndex
from models import ModelContainer
from service import SimulationService
from viewmodels import (
    PlantViewModel, LanguageViewModel, PlotViewModel, FunctionViewModel, ControllerViewModel,
    PsoConfigurationViewModel, EvaluationViewModel
)


class AppEngine:
    """Main application engine that initializes domain services and ViewModels.

    Responsibilities:
        - Initialize logging
        - Initialize simulation services
        - Perform PSO warmup
        - Instantiate ViewModels and model containers
    """

    def __init__(self):
        """Initialize the application engine."""
        # ------------------------------
        # Logger
        # ------------------------------
        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Starting new Application Engine.")

        # ------------------------------
        # Simulation services
        # ------------------------------
        self.simulation_service = SimulationService()

        # ------------------------------
        # PSO warmup
        # ------------------------------
        # This performs a minimal PSO run to pre-compile and initialize
        # the PSO engine for faster subsequent simulations.
        self.pso_warmup()

        # ------------------------------
        # Model containers
        # ------------------------------
        self.model_container = ModelContainer()

        # ------------------------------
        # ViewModels
        # ------------------------------
        # Language ViewModel (e.g., for translations)
        self.vm_lang = LanguageViewModel(self.model_container.model_settings)

        # Plant plots and controls
        self.vm_plot_plant = PlotViewModel()
        self.vm_plant = PlantViewModel(self.model_container, self.simulation_service)

        # Function plots and controls
        self.vm_plot_function = PlotViewModel()
        self.vm_function = FunctionViewModel(self.model_container.model_function, self.simulation_service)

        # Controller ViewModel
        self.vm_controller = ControllerViewModel(self.model_container.model_controller)

        # PSO configuration ViewModel
        self.vm_pso = PsoConfigurationViewModel(self.model_container, self.simulation_service)

        # Evaluation ViewModel
        self.vm_evaluator = EvaluationViewModel(self.model_container.model_evaluator, self.vm_pso)

        self.logger.info("Application Engine initialization completed.")

    # ------------------------------
    # PSO Warmup Method
    # ------------------------------
    def pso_warmup(self):
        """Perform a minimal PSO simulation to warm up the engine.

        This pre-compiles any JIT functions, initializes caches, and
        triggers one-time setup in the PSO engine for faster subsequent runs.
        """

        # Minimal PSO parameters for warmup
        pso_param = PsoSimulationParam(
            num=[1],
            den=[1, 2, 1],
            t0=0,
            t1=10,
            dt=1e-4,
            solver=MySolver.RK4,
            anti_windup=AntiWindup.CLAMPING,
            constraint=(-5, 5),
            excitation_target=ExcitationTarget.REFERENCE,
            function=lambda t: np.zeros_like(t),  # zero reference
            performance_index=PerformanceIndex.ITAE,
            kp=(0, 10),
            ti=(1e-9, 10),
            td=(0, 10),
            swarm_size=40,
            pso_iteration=1  # only one iteration for warmup
        )

        self.logger.info("Starting PSO engine warmup.")

        # Run warmup simulation asynchronously
        self.simulation_service.run_pso_simulation(
            pso_param,
            callback=lambda result: self.logger.info("PSO warmup completed successfully."),
            progress_callback=lambda iteration: self.logger.debug(
                "PSO warmup iteration %d completed.", iteration
            )
        )
