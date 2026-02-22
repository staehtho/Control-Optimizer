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

def test_function_change(model, vm, qtbot):

    model._selected_function = SineFunction()

    with qtbot.waitSignal(vm.functionChanged, timeout=100):
        vm.set_selected_function(Functions.UNIT_STEP)

    assert vm.selected_function.get_formula() == Functions.UNIT_STEP.value().get_formula()

def test_compute_finished(model, vm, qtbot):
    model._selected_function = UnitStepFunction()

    spy = QSignalSpy(vm.computeFinished)

    with qtbot.waitSignal(vm.computeFinished, timeout=500):
        vm.compute_function(0, 1)

    assert spy.size() == 1