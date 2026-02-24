import pytest
from PySide6.QtTest import QSignalSpy

from models import ModelContainer
from viewmodels import PsoConfigurationViewModel

@pytest.fixture
def model_container() -> ModelContainer:
    return ModelContainer()

@pytest.fixture
def vm_pso(model_container: ModelContainer) -> PsoConfigurationViewModel:
    return PsoConfigurationViewModel(model_container)

def test_plant_changed(model_container: ModelContainer, vm_pso: PsoConfigurationViewModel, qtbot) -> None:
    model_container.model_plant.num= [1]
    model_container.model_plant.den = [1, 1]

    with qtbot.waitSignal(vm_pso.plantChanged, timeout=500):
        model_container.model_plant.num = [2]
        model_container.model_plant.den = [1, 1, 1]

    assert vm_pso.get_plant_num_den() == ([2], [1, 1, 1])

@pytest.mark.parametrize(
    "start_time, expected_spy_size",
    [
        (0.0, 0),
        (0.5, 1),
        (1.0, 0)
    ],
    ids=[
        "t = t0",
        "t0 < t < t1",
        "t = t1"
    ]
)
def test_start_time_changed(model_container: ModelContainer, vm_pso: PsoConfigurationViewModel, start_time, expected_spy_size) -> None:
    model_container.model_pso.start_time = 0.0
    model_container.model_pso.end_time = 1.0

    spy = QSignalSpy(vm_pso.starTimeChanged)

    vm_pso.start_time = start_time

    assert spy.size() == expected_spy_size
    assert vm_pso.start_time == model_container.model_pso.start_time

@pytest.mark.parametrize(
    "end_time, expected_spy_size",
    [
        (0.0, 0),
        (0.5, 1),
        (1.0, 0)
    ],
    ids=[
        "t = t0",
        "t0 < t < t1",
        "t = t1"
    ]
)
def test_end_time_changed(model_container: ModelContainer, vm_pso: PsoConfigurationViewModel, end_time, expected_spy_size) -> None:
    model_container.model_pso.start_time = 0.0
    model_container.model_pso.end_time = 1.0

    spy = QSignalSpy(vm_pso.endTimeChanged)

    vm_pso.end_time = end_time

    assert spy.size() == expected_spy_size
    assert vm_pso.end_time == model_container.model_pso.end_time