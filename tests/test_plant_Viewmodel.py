from unittest.mock import MagicMock

import pytest
from PySide6.QtTest import QSignalSpy

from models import ModelContainer
from service import SimulationService
from viewmodels import PlantViewModel


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
def plant_vm(model_container: ModelContainer, mock_simulation_service) -> PlantViewModel:
    return PlantViewModel(model_container, mock_simulation_service)

@pytest.mark.parametrize(
    "text, array",
    [
        ("1, 2, 3", [1.0, 2.0, 3.0]),
        ("1 2 3", [1.0, 2.0, 3.0]),
        ("1; 2; 3", [1.0, 2.0, 3.0]),
        ("1.8 2.8, 3.4", [1.8, 2.8, 3.4]),
    ],
    ids=[
        "int value, seperator: ,",
        "int value, seperator: ",
        "int value, seperator: ;",
        "float value, seperator: ,",
    ]

)
def test_plant_vm_str2array(plant_vm: PlantViewModel, text, array):
    assert plant_vm._str2array(text) == array

@pytest.mark.parametrize(
    "num1, num2, expected_size",
    [
        ("1, 1, 1", "1, 1, 1", 1),
        ("1", "1, 1", 2),
    ],
    ids=[
        "same value",
        "different value"
    ]
)
def test_plant_vm_update_num(model_container: ModelContainer, plant_vm: PlantViewModel, num1, num2, expected_size):

    spy = QSignalSpy(plant_vm.numChanged)

    plant_vm.update_num(num1)
    plant_vm.update_num(num2)

    assert spy.size() == expected_size
    assert plant_vm._num_input == num2
    assert len(model_container.model_pso.num) == len(num2.split(","))

@pytest.mark.parametrize(
    "den1, den2, expected_size",
    [
        ("1, 1, 1", "1, 1, 1", 1),
        ("1", "1, 1", 2),
    ],
    ids=[
        "same value",
        "different value"
    ]
)
def test_plant_vm_update_den(model_container: ModelContainer, plant_vm: PlantViewModel, den1, den2, expected_size):

    spy = QSignalSpy(plant_vm.denChanged)

    plant_vm.update_den(den1)
    plant_vm.update_den(den2)

    assert spy.size() == expected_size
    assert plant_vm._den_input == den2
    assert len(model_container.model_pso.den) == len(den2.split(","))