from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, Callable

from app_types import PlantResponseContext, PsoSimulationParam
from app_domain.functions import StepFunction
from models import ModelContainer
from service import SimulationService
from .controlsys import ControllerType
from .ui_context import UiContext

if TYPE_CHECKING:
    from viewmodels import (
        PlotViewModel, BodePlotViewModel, FunctionViewModel,
        LanguageViewModel, ThemeViewModel, PlantViewModel,
        ControllerViewModel, PsoConfigurationViewModel,
        EvaluationViewModel, SimulationViewModel, SettingsViewModel, DataManagementViewModel
    )

T = TypeVar("T")


class AppEngine:
    """
    Central application engine and composition root for MVVM architecture.

    Responsibilities:
        - Initialize core services (logging, simulation, models)
        - Provide lazy factories for all ViewModels
        - Cache ViewModels for singleton access
        - Reduce startup time via deferred instantiation
        - Serve as dependency provider for the UI layer
    """

    # ==========================================================
    # Initialization
    # ==========================================================
    def __init__(self):
        """
        Initialize the application engine.
        """
        # ------------------------------
        # Logger
        # ------------------------------
        self.logger = logging.getLogger(f"AppEngine.{self.__class__.__name__}")
        self.logger.info("Starting Application Engine...")

        # ------------------------------
        # Core services
        # ------------------------------
        self.simulation_service = SimulationService()

        # ------------------------------
        # Domain models
        # ------------------------------
        self.model_container = ModelContainer()

        # ------------------------------
        # Typed singleton ViewModel attributes (lazy)
        # ------------------------------
        self._vm_language: LanguageViewModel | None = None
        self._vm_theme: ThemeViewModel | None = None
        self._vm_settings: SettingsViewModel | None = None
        self._vm_plant: PlantViewModel | None = None
        self._vm_controller: ControllerViewModel | None = None
        self._vm_pso: PsoConfigurationViewModel | None = None
        self._vm_evaluator: EvaluationViewModel | None = None
        self._vm_simulation: SimulationViewModel | None = None
        self._vm_data: DataManagementViewModel | None = None

        # ------------------------------
        # Keyed ViewModel caches
        # ------------------------------
        self._vm_plots: dict[str, PlotViewModel] = {}
        self._vm_bode_plots: dict[str, BodePlotViewModel] = {}
        self._vm_functions: dict[str, FunctionViewModel] = {}

        # ------------------------------
        # UI context (uses lazy factories)
        # ------------------------------
        self.ui_context = UiContext(
            settings=self.ensure_settings_viewmodel(),
            vm_lang=self.ensure_language_viewmodel(),
            vm_theme=self.ensure_theme_viewmodel(),
        )

        self.logger.info("Application Engine initialized.")

    # ==========================================================
    # Generic factory helper
    # ==========================================================
    @staticmethod
    def _get_or_create(cache: dict[str, T], key: str, factory: Callable[[], T]) -> T:
        """
        Retrieve an instance from cache or create it lazily.

        Args:
            cache: Dictionary storing instances
            key: Unique identifier for the instance
            factory: Callable that creates the instance

        Returns:
            Cached or newly created instance
        """
        vm = cache.get(key)
        if vm is None:
            vm = factory()
            cache[key] = vm
        return vm

    # ==========================================================
    # Generic lazy helper for typed singletons
    # ==========================================================
    def _ensure(self, attr_name: str, factory: Callable[[], T]) -> T:
        """
        Retrieve a cached ViewModel or create it lazily.

        Args:
            attr_name: Name of the attribute storing the ViewModel
            factory: Callable that creates the ViewModel if missing

        Returns:
            The cached or newly created ViewModel instance
        """
        vm = getattr(self, attr_name)
        if vm is None:
            vm = factory()
            setattr(self, attr_name, vm)
        return vm

    # ==========================================================
    # Singleton-style ViewModel factories
    # ==========================================================
    def ensure_language_viewmodel(self) -> LanguageViewModel:
        from viewmodels import LanguageViewModel
        return self._ensure("_vm_language", lambda: LanguageViewModel(self.model_container.model_settings))

    def ensure_theme_viewmodel(self) -> ThemeViewModel:
        from viewmodels import ThemeViewModel
        return self._ensure("_vm_theme", lambda: ThemeViewModel(self.model_container.model_settings))

    def ensure_settings_viewmodel(self) -> SettingsViewModel:
        from viewmodels import SettingsViewModel
        return self._ensure("_vm_settings", lambda: SettingsViewModel(self.model_container.model_settings))

    def ensure_plant_viewmodel(self) -> PlantViewModel:
        from viewmodels import PlantViewModel
        return self._ensure("_vm_plant", lambda: PlantViewModel(self.model_container, self.simulation_service))

    def ensure_controller_viewmodel(self) -> ControllerViewModel:
        from viewmodels import ControllerViewModel
        return self._ensure("_vm_controller", lambda: ControllerViewModel(self.model_container.model_controller))

    def ensure_pso_viewmodel(self) -> PsoConfigurationViewModel:
        from viewmodels import PsoConfigurationViewModel
        return self._ensure(
            "_vm_pso",
            lambda: PsoConfigurationViewModel(
                self.model_container,
                self.ensure_controller_viewmodel(),
                self.simulation_service
            )
        )

    def ensure_evaluator_viewmodel(self) -> EvaluationViewModel:
        from viewmodels import EvaluationViewModel
        return self._ensure(
            "_vm_evaluator",
            lambda: EvaluationViewModel(
                self.model_container.model_settings,
                self.ensure_pso_viewmodel(),
                self.simulation_service
            )
        )

    def ensure_simulation_viewmodel(self) -> SimulationViewModel:
        from viewmodels import SimulationViewModel
        from app_domain.controlsys import ExcitationTarget
        def factory():
            model_functions = {
                i.name: self.model_container.ensure_function_model(i.name)
                for i in ExcitationTarget
            }
            return SimulationViewModel(
                model_functions,
                self.model_container.model_settings,
                self.ensure_pso_viewmodel(),
                self.simulation_service
            )

        return self._ensure("_vm_simulation", factory)

    def ensure_data_viewmodel(self) -> DataManagementViewModel:
        from viewmodels import DataManagementViewModel
        return self._ensure(
            "_vm_data",
            lambda: DataManagementViewModel(
                self,
                self.ensure_evaluator_viewmodel(),
                self.model_container
            )
        )

    # ==========================================================
    # Keyed ViewModel factories
    # ==========================================================
    def ensure_plot_viewmodel(self, key: str) -> PlotViewModel:
        from viewmodels.plot_viewmodel import PlotViewModel
        return self._get_or_create(self._vm_plots, key, PlotViewModel)

    def ensure_bode_plot_viewmodel(self, key: str) -> BodePlotViewModel:
        from viewmodels.bode_plot_viewmodel import BodePlotViewModel
        return self._get_or_create(self._vm_bode_plots, key, BodePlotViewModel)

    def ensure_function_viewmodel(self, key: str) -> FunctionViewModel:
        from viewmodels.function_viewmodel import FunctionViewModel
        return self._get_or_create(
            self._vm_functions,
            key,
            lambda: FunctionViewModel(self.model_container.ensure_function_model(key), self.simulation_service)
        )

    # ==========================================================
    # Step Response Warmup routine
    # ==========================================================
    def step_response_warmup(self):
        """Perform a minimal step response to warm up the engine.

        This pre-compiles any JIT functions, initializes caches, and
        triggers one-time setup in the step response engine for faster subsequent runs.
        """
        import numpy as np
        from app_domain.controlsys import MySolver
        self.logger.info("Starting step response engine warmup.")

        context = PlantResponseContext(
            num=[1],
            den=[1, 2, 1],
            t0=0,
            t1=10,
            solver=MySolver.RK4,
            reference=lambda t: np.where(t >= 0, 1.0, 0.0),
        )

        # Run warmup simulation asynchronously
        self.simulation_service.compute_plant_response(context, callback=lambda t, y: self.logger.info(
            "Step response warmup completed successfully."))

    # ==========================================================
    # PSO Warmup routine
    # ==========================================================
    def pso_warmup(self):
        """Perform a minimal PSO simulation to warm up the engine.

        This pre-compiles any JIT functions, initializes caches, and
        triggers one-time setup in the PSO engine for faster subsequent runs.
        """
        from app_domain.controlsys import MySolver, AntiWindup, ExcitationTarget, PerformanceIndex, PIDClosedLoop
        # Minimal PSO parameters for warmup
        pso_param = PsoSimulationParam(
            num=[1],
            den=[1, 2, 1],
            controller_type=ControllerType.PID,
            controller_param_names=['kp', 'ti', 'td'],
            controller_class=PIDClosedLoop,
            t0=0,
            t1=10,
            dt=1e-4,
            tuning_factor=5.0,
            limit_factor=5.0,
            sampling_rate=None,
            solver=MySolver.RK4,
            anti_windup=AntiWindup.CLAMPING,
            ka=1.0,
            constraint=(-5, 5),
            excitation_target=ExcitationTarget.REFERENCE,
            function=StepFunction(),
            bounds=(
                [0, 0.001, 0],
                [10, 10, 10]
            ),
            n_param=3,
            swarm_size=40,
            pso_iteration=1,  # only one iteration for warmup
            error_criterion=PerformanceIndex.ITAE,
            slew_rate_max=2,
            slew_window_size=10,
            slew_rate_limit_enabled=True,
            overshoot_control=5,
            overshoot_control_enabled=True,
            gain_margin=16,
            gain_margin_enabled=True,
            phase_margin=60,
            phase_margin_enabled=True,
            stability_margin=6.0,
            stability_margin_enabled=True,
            omega_exp_low=-5,
            omega_exp_high=5,
            omega_points=500,
            hyperparameters=self.model_container.model_settings.get_pso_hyper_parameters()
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

    def run_warmup(self, runs: int = 2) -> None:
        """Run PSO warmup multiple times to prime caches/JIT."""
        for _ in range(max(0, runs)):
            self.pso_warmup()

    def export_project_state(self) -> dict:
        return self.model_container.export_project_state()

    def save_project(self, path: str | Path) -> Path:
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")

        payload = self.export_project_state()
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.logger.info("Project state saved to %s", target)
        return target

    def load_project(self, path: str | Path) -> None:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        self.model_container.import_project_state(payload)
        self.refresh_ui_from_models()
        self.logger.info("Project state loaded from %s", source)

    def refresh_ui_from_models(self) -> None:
        self.ensure_settings_viewmodel().refresh_from_model()
        self.ensure_language_viewmodel().refresh_from_model()
        self.ensure_theme_viewmodel().refresh_from_model()

        self.ensure_controller_viewmodel().refresh_from_model()
        self.ensure_plant_viewmodel().refresh_from_model()
        self.ensure_pso_viewmodel().refresh_from_model()

        for vm in self._vm_functions.values():
            vm.refresh_from_model()

    def shutdown(self) -> None:
        """Stop background workers before the application exits."""
        self.logger.info("Shutting down AppEngine.")
        self.simulation_service.shutdown()

