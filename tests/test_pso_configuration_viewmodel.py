import pytest
from PySide6.QtTest import QSignalSpy
from unittest.mock import MagicMock

from app_domain.controlsys import PerformanceIndex, ExcitationTarget
from service import SimulationService
from models import ModelContainer
from viewmodels import PsoConfigurationViewModel


@pytest.fixture
def mock_simulation_service():
    service = MagicMock(spec=SimulationService)
    # Optional: definiere, was compute oder andere Methoden zurückgeben sollen
    service.compute_function.return_value = None
    return service

@pytest.fixture
def model_container() -> ModelContainer:
    return ModelContainer()

@pytest.fixture
def vm_pso(model_container: ModelContainer, mock_simulation_service) -> PsoConfigurationViewModel:
    return PsoConfigurationViewModel(model_container, mock_simulation_service)

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("start_time", "end_time", "startTimeChanged", 0, 1, 0.0, 0),
        ("start_time", "end_time", "startTimeChanged", 0, 1, 0.5, 1),
        ("start_time", "end_time", "startTimeChanged", 0, 1, 1.0, 0),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 0.0, 0),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 0.5, 1),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 1.0, 0),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 0.0, 0),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 0.5, 1),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 1.0, 0),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 0.0, 0),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 0.5, 1),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 1.0, 0)
    ],
    ids=[
        "start_time: min == val",
        "start_time: min < val < max",
        "start_time: val == max",
        "kp_min: min == val",
        "kp_min: min < val < max",
        "kp_min: val == max",
        "ti_min: min == val",
        "ti_min: min < val < max",
        "ti_min: val == max",
        "td_min: min == val",
        "td_min: min < val < max",
        "td_min: val == max",
    ]
)
def test_min_value_with_verification_changed(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_container.model_pso, attribute_min, init_min)
    setattr(model_container.model_pso, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_pso, signal))

    setattr(vm_pso, attribute_min, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_pso, attribute_min) == getattr(model_container.model_pso, attribute_min)

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("start_time", "end_time", "endTimeChanged", 0, 1, 0.0, 0),
        ("start_time", "end_time", "endTimeChanged", 0, 1, 0.5, 1),
        ("start_time", "end_time", "endTimeChanged", 0, 1, 1.0, 0),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 0.0, 0),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 0.5, 1),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 1.0, 0),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 0.0, 0),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 0.5, 1),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 1.0, 0),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 0.0, 0),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 0.5, 1),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 1.0, 0)
    ],
    ids=[
        "end_time: min == val",
        "end_time: min < val < max",
        "end_time: val == max",
        "kp_max: min == val",
        "kp_max: min < val < max",
        "kp_max: val == max",
        "ti_max: min == val",
        "ti_max: min < val < max",
        "ti_max: val == max",
        "td_max: min == val",
        "td_max: min < val < max",
        "td_max: val == max",
    ]
)
def test_max_value_with_verification_changed(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_container.model_pso, attribute_min, init_min)
    setattr(model_container.model_pso, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_pso, signal))

    setattr(vm_pso, attribute_max, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_pso, attribute_max) == getattr(model_container.model_pso, attribute_max)


@pytest.mark.parametrize(
    "attribute, signal, init_value, value, spy_size",
    [
        ("excitation_target", "excitationTargetChanged", ExcitationTarget.REFERENCE, ExcitationTarget.INPUT_DISTURBANCE,
         1),
        ("excitation_target", "excitationTargetChanged", ExcitationTarget.REFERENCE, ExcitationTarget.REFERENCE, 0),
        ("performance_index", "performanceIndexChanged", PerformanceIndex.ITAE, PerformanceIndex.IAE, 1),
        ("performance_index", "performanceIndexChanged", PerformanceIndex.ITAE, PerformanceIndex.ITAE, 0),
    ],
    ids=[
        "excitation_target value changed",
        "excitation_target no value changed",
        "performance_index value changed",
        "performance_index no value changed",
    ]
)
def test_value_changed(model_container: ModelContainer, vm_pso: PsoConfigurationViewModel,
                       attribute, signal, init_value, value, spy_size) -> None:

    setattr(model_container.model_pso, attribute, init_value)

    spy = QSignalSpy(getattr(vm_pso, signal))

    setattr(vm_pso, attribute, value)

    assert getattr(model_container.model_pso, attribute) == getattr(vm_pso, attribute)
    assert spy.size() == spy_size
