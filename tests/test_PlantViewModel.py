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
    "num",
    [
        ([1, 1, 1]),
        ([1, 1, 1, 1])
    ]
)
def test_plant_vm_num_changed(plant_model: PlantModel, plant_vm: PlantViewModel, num, qtbot):

    with qtbot.waitSignal(plant_vm.numChanged, timeout=100):
        plant_vm.num = num

    assert plant_vm.num == plant_model.num == num

@pytest.mark.parametrize(
    "den",
    [
        ([1, 1, 1]),
        ([1, 1, 1, 1])
    ]
)
def test_plant_vm_den_changed(plant_model: PlantModel, plant_vm: PlantViewModel, den, qtbot):

    with qtbot.waitSignal(plant_vm.denChanged, timeout=100):
        plant_vm.den = den

    assert plant_vm.den == plant_model.den == den

@pytest.mark.parametrize(
    "num, den, expected",
    [
        ([1, 1, 1], [1, 1, 1], True),
        ([1, 1, 1, 1], [], False),
    ]
)
def test_plant_vm_is_valid(plant_model: PlantModel, plant_vm: PlantViewModel, num, den, expected, qtbot):

    spy_is_valid = QSignalSpy(plant_vm.isValidChanged)
    spy_num = QSignalSpy(plant_vm.numChanged)
    spy_den = QSignalSpy(plant_vm.denChanged)

    plant_vm.num = num
    plant_vm.den = den

    if expected:
        assert spy_is_valid.size() == 1
        assert spy_num.size() == 1
        assert spy_den.size() == 1
        assert len(plant_vm.num) == len(plant_model.num) == len(num) == len(plant_model.get_plant().num)
        assert len(plant_vm.den) == len(plant_model.den) == len(den) == len(plant_model.get_plant().den)
    else:
        assert spy_is_valid.size() == 0
        assert spy_num.size() == (1 if len(num) > 0 else 0)
        assert spy_den.size() == (1 if len(den) > 0 else 0)