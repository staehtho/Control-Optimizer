import pytest
from PySide6.QtTest import QSignalSpy

from models import FunctionModel, Functions
from models.functionModel import UnitStepFunction, SineFunction
from viewmodels import FunctionViewModel

@pytest.fixture
def model() -> FunctionModel:
    return FunctionModel()

@pytest.fixture
def vm(model: FunctionModel) -> FunctionViewModel:
    return FunctionViewModel(model)

@pytest.mark.parametrize(
    "t0, expected_t0, expected_spy",
    [
        (0.0, 0.0, 0),
        (0.5, 0.5, 1),
        (1.0, 0.0, 1)
    ],
    ids=[
        "t0 == t0",
        "t0 < t1",
        "t0 == t1",
    ]
)
def test_t0_change(model, vm, t0, expected_t0, expected_spy):
    model._t0 = 0.0
    model._t1 = 1.0

    spy = QSignalSpy(vm.t0Changed)

    vm.t0 = t0

    assert vm.t0 == expected_t0
    assert spy.size() == expected_spy

@pytest.mark.parametrize(
    "t1, expected_t1, expected_spy",
    [
        (1.0, 1.0, 0),
        (0.5, 0.5, 1),
        (0.0, 1.0, 1)
    ],
    ids=[
        "t1 == t1",
        "t1 > t0",
        "t0 == t1",
    ]
)
def test_t1_change(model, vm, t1, expected_t1, expected_spy):
    model._t0 = 0.0
    model._t1 = 1.0

    spy = QSignalSpy(vm.t1Changed)

    vm.t1 = t1

    assert vm.t1 == expected_t1
    assert spy.size() == expected_spy

def test_function_change(model, vm, qtbot):

    model._function = SineFunction()

    with qtbot.waitSignal(vm.functionChanged, timeout=100):
        vm.set_function(Functions.UNIT_STEP)

    assert vm.function.get_formula() == Functions.UNIT_STEP.value().get_formula()

def test_compute_finished(model, vm, qtbot):
    model._function = UnitStepFunction()
    model._t0 = 0.0
    model._t1 = 1.0

    spy = QSignalSpy(vm.computeFinished)

    with qtbot.waitSignal(vm.computeFinished, timeout=500):
        vm.compute_function()

    assert spy.size() == 1