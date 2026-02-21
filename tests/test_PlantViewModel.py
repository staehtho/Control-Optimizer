import pytest
from PySide6.QtTest import QSignalSpy

from models import PlantModel
from viewmodels import PlantViewModel

@pytest.fixture
def plant_model() -> PlantModel:
    return PlantModel()

@pytest.fixture
def plant_vm(plant_model: PlantModel) -> PlantViewModel:
    return PlantViewModel(plant_model)

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
def test_plant_vm_update_num(plant_model: PlantModel, plant_vm: PlantViewModel, num1, num2, expected_size):

    spy = QSignalSpy(plant_vm.numChanged)

    plant_vm.update_num(num1)
    plant_vm.update_num(num2)

    assert spy.size() == expected_size
    assert plant_vm._num_input == num2

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
def test_plant_vm_update_den(plant_model: PlantModel, plant_vm: PlantViewModel, den1, den2, expected_size):

    spy = QSignalSpy(plant_vm.denChanged)

    plant_vm.update_den(den1)
    plant_vm.update_den(den2)

    assert spy.size() == expected_size
    assert plant_vm._den_input == den2

@pytest.mark.parametrize(
    "num, den, expected",
    [
        ("1, 1, 1", "1, 1, 1", True),
        ("1, 1, 1, 1", "", False),
    ]
)
def test_plant_vm_is_valid(plant_vm: PlantViewModel, num, den, expected):

    spy_is_valid = QSignalSpy(plant_vm.isValidChanged)
    spy_num = QSignalSpy(plant_vm.numChanged)
    spy_den = QSignalSpy(plant_vm.denChanged)

    plant_vm.update_num(num)
    plant_vm.update_den(den)

    if expected:
        assert spy_is_valid.size() == 1
        assert spy_num.size() == 1
        assert spy_den.size() == 1
        assert plant_vm.is_valid == expected
    else:
        assert spy_is_valid.size() == 0
        assert spy_num.size() == (1 if len(num) > 0 else 0)
        assert spy_den.size() == (1 if len(den) > 0 else 0)
        assert plant_vm.is_valid == expected