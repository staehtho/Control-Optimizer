from PySide6.QtTest import QSignalSpy

from models.functionModel import FunctionModel, Functions, SineFunction, UnitStepFunction


def test_set_function(qtbot):
    function = FunctionModel()
    function._function = SineFunction()

    with qtbot.waitSignal(function.functionChanged, timeout=100):
        function.set_function(Functions.UNIT_STEP_FUNCTION.name)

    assert function.function.get_function() == Functions.UNIT_STEP_FUNCTION.value().get_function()

def test_compute_function(qtbot):
    function = FunctionModel()
    function._function = UnitStepFunction()

    spy = QSignalSpy(function.computeFinished)

    with qtbot.waitSignal(function.computeFinished, timeout=500):
        function.compute(0, 10)

    assert spy.size() == 1