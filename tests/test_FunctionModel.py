import pytest
from PySide6.QtTest import QSignalSpy

from models.functionModel import FunctionModel, Functions, SineFunction, UnitStepFunction


def test_set_function(qtbot):
    function = FunctionModel()
    function._selected_function = SineFunction()

    with qtbot.waitSignal(function.functionChanged, timeout=100):
        function.set_selected_function(Functions.UNIT_STEP)

    assert function.selected_function.get_formula() == Functions.UNIT_STEP.value().get_formula()


def test_compute_function(qtbot):
    function = FunctionModel()
    function._selected_function = UnitStepFunction()
    function._t0 = 0.0
    function._t1 = 1.0

    spy = QSignalSpy(function.computeFinished)

    with qtbot.waitSignal(function.computeFinished, timeout=500):
        function.compute(0, 1)

    assert spy.size() == 1

@pytest.mark.parametrize(
    "value, key, expected_value, expected_spy_size",
    [
        (0, "A", 0, 0),
        (1, r"\varphi", 1, 1),
        (0.5, r"\omega", 0.5, 1)
    ],
    ids=[
        "same value",
        "different value",
        "different (float) value"
    ]
)

def test_param_value_changed(value, key, expected_value, expected_spy_size):
    function = FunctionModel()

    function._selected_function = SineFunction()
    function.selected_function._param[key] = 0

    spy = QSignalSpy(function.parameterChanged)

    function.update_param_value(key, value)
    print(function.selected_function._param)

    assert spy.size() == expected_spy_size
    assert function.selected_function.get_param_value(key) == expected_value

