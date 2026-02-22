import pytest
from PySide6.QtTest import QSignalSpy

from models.functionModel import FunctionModel, Functions, SineFunction, UnitStepFunction


def test_set_function(qtbot):
    function = FunctionModel()
    function._function = SineFunction()

    with qtbot.waitSignal(function.functionChanged, timeout=100):
        function.set_function(Functions.UNIT_STEP)

    assert function.function.get_formula() == Functions.UNIT_STEP.value().get_formula()

@pytest.mark.parametrize(
    "t0, expected_spy",
    [
        (0.0, 0),
        (0.5, 1),
        (1.0, 0)
    ],
    ids=[
        "t0 == t0",
        "t0 < t1",
        "t0 == t1",
    ]
)
def test_t0_change(t0, expected_spy):
    function = FunctionModel()
    function._t0 = 0
    function._t1 = 1.0

    spy = QSignalSpy(function.t0Changed)

    function.t0 = t0

    assert spy.size() == expected_spy


@pytest.mark.parametrize(
    "t1, expected_spy",
    [
        (1.0, 0),
        (0.5, 1),
        (0.0, 0)
    ],
    ids=[
        "t1 == t1",
        "t1 > t0",
        "t0 == t1",
    ]
)
def test_t1_change(t1, expected_spy):
    function = FunctionModel()
    function._t0 = 0
    function._t1 = 1.0

    spy = QSignalSpy(function.t1Changed)

    function.t1 = t1

    assert spy.size() == expected_spy


def test_compute_function(qtbot):
    function = FunctionModel()
    function._function = UnitStepFunction()
    function._t0 = 0.0
    function._t1 = 1.0

    spy = QSignalSpy(function.computeFinished)

    with qtbot.waitSignal(function.computeFinished, timeout=500):
        function.compute()

    assert spy.size() == 1