import pytest
from PySide6.QtTest import QSignalSpy

from app_domain.functions import FunctionTypes, SineFunction
from models import FunctionModel


def test_set_function(qtbot):
    function = FunctionModel(SineFunction())

    with qtbot.waitSignal(function.functionChanged, timeout=100):
        function.set_selected_function(FunctionTypes.STEP)

    assert function.selected_function.get_formula() == FunctionTypes.STEP.value().get_formula()

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
    function = FunctionModel(SineFunction())

    function.selected_function._param[key] = 0

    spy = QSignalSpy(function.parameterChanged)

    function.update_param_value(key, value)
    print(function.selected_function._param)

    assert spy.size() == expected_spy_size
    assert function.selected_function.get_param_value(key) == expected_value

