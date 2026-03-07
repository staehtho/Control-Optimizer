from unittest.mock import MagicMock

import pytest
from PySide6.QtTest import QSignalSpy

from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from models import ModelContainer
from service import SimulationService
from viewmodels import PsoConfigurationViewModel


@pytest.fixture
def mock_simulation_service() -> MagicMock:
    return MagicMock(spec=SimulationService)


@pytest.fixture
def model_container() -> ModelContainer:
    return ModelContainer()


@pytest.fixture
def vm_pso(model_container: ModelContainer, mock_simulation_service: MagicMock) -> PsoConfigurationViewModel:
    return PsoConfigurationViewModel(model_container, mock_simulation_service)


@pytest.mark.parametrize(
    ("attribute", "signal", "initial", "new_value", "expected_value", "expected_signal_count"),
    [
        ("t0", "t0Changed", 0.0, 0.5, 0.5, 1),
        ("t0", "t0Changed", 0.0, 1.0, 0.0, 0),
        ("t1", "t1Changed", 1.0, 1.5, 1.5, 1),
        ("t1", "t1Changed", 1.0, 0.0, 1.0, 0),
        ("kp_min", "kpMinChanged", 0.0, 0.5, 0.5, 1),
        ("kp_min", "kpMinChanged", 0.0, 1.0, 0.0, 0),
        ("kp_max", "kpMaxChanged", 1.0, 2.0, 2.0, 1),
        ("kp_max", "kpMaxChanged", 1.0, 0.0, 1.0, 0),
        ("ti_min", "tiMinChanged", 1e-9, 0.0, 1e-9, 1),  # transformed from 0 to 1e-9
        ("td_min", "tdMinChanged", 0.0, 0.5, 0.5, 1),
        ("td_max", "tdMaxChanged", 1.0, 2.0, 2.0, 1),
    ],
)
def test_numeric_property_validation_and_signal_behavior(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute: str,
        signal: str,
        initial: float,
        new_value: float,
        expected_value: float,
        expected_signal_count: int,
) -> None:
    # Keep all min/max constraints coherent for each specific attribute check.
    model_container.model_pso.t0 = 0.0
    model_container.model_pso.t1 = 1.0
    model_container.model_pso.kp_min = 0.0
    model_container.model_pso.kp_max = 1.0
    model_container.model_pso.ti_min = 1e-9
    model_container.model_pso.ti_max = 1.0
    model_container.model_pso.td_min = 0.0
    model_container.model_pso.td_max = 1.0

    setattr(model_container.model_pso, attribute, initial)

    spy = QSignalSpy(getattr(vm_pso, signal))
    setattr(vm_pso, attribute, new_value)

    assert spy.size() == expected_signal_count
    assert getattr(vm_pso, attribute) == expected_value


@pytest.mark.parametrize(
    ("attribute", "signal", "initial", "new_value", "expected_signal_count"),
    [
        ("excitation_target", "excitationTargetChanged", ExcitationTarget.REFERENCE, ExcitationTarget.INPUT_DISTURBANCE,
         1),
        ("excitation_target", "excitationTargetChanged", ExcitationTarget.REFERENCE, ExcitationTarget.REFERENCE, 1),
        ("performance_index", "performanceIndexChanged", PerformanceIndex.ITAE, PerformanceIndex.IAE, 1),
        ("performance_index", "performanceIndexChanged", PerformanceIndex.ITAE, PerformanceIndex.ITAE, 1),
    ],
)
def test_enum_property_change_behavior(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute: str,
        signal: str,
        initial,
        new_value,
        expected_signal_count: int,
) -> None:
    setattr(model_container.model_pso, attribute, initial)

    spy = QSignalSpy(getattr(vm_pso, signal))
    setattr(vm_pso, attribute, new_value)

    assert spy.size() == expected_signal_count
    assert getattr(model_container.model_pso, attribute) == getattr(vm_pso, attribute)


def test_run_pso_simulation_does_not_call_service_when_plant_invalid(
        vm_pso: PsoConfigurationViewModel,
        mock_simulation_service: MagicMock,
) -> None:
    mock_simulation_service.run_pso_simulation.reset_mock()

    vm_pso.run_pso_simulation()

    assert mock_simulation_service.run_pso_simulation.call_count == 0


def test_run_pso_simulation_calls_service_when_plant_valid(
        model_container: ModelContainer,
        mock_simulation_service: MagicMock,
) -> None:
    model_container.model_plant.num = [1.0]
    model_container.model_plant.den = [1.0, 1.0]

    vm = PsoConfigurationViewModel(model_container, mock_simulation_service)

    assert mock_simulation_service.run_pso_simulation.call_count == 1

    pso_param, callback, progress_callback = mock_simulation_service.run_pso_simulation.call_args.args
    assert pso_param.num == [1.0]
    assert pso_param.den == [1.0, 1.0]
    assert callable(callback)
    assert callable(progress_callback)

    # Explicit second run should trigger another call.
    vm.run_pso_simulation()
    assert mock_simulation_service.run_pso_simulation.call_count == 2


'''def test_progress_and_finished_signals(vm_pso: PsoConfigurationViewModel) -> None:
    spy_progress = QSignalSpy(vm_pso.psoProgressChanged)
    spy_finished = QSignalSpy(vm_pso.psoSimulationFinished)

    vm_pso._on_pso_progress(3)
    vm_pso._on_pso_simulation_finished(PsoResult(
        10, ExcitationTarget.REFERENCE, StepFunction(), 10, 5, 1, 0.1, 0, 10
    ))

    assert spy_progress.size() == 1
    assert spy_finished.size() == 1
    assert vm_pso.get_pso_result() is not None'''
