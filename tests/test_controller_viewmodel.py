import pytest
from PySide6.QtTest import QSignalSpy

from app_domain.controlsys import AntiWindup
from models import ControllerModel
from viewmodels import ControllerViewModel

@pytest.fixture
def model_controller() -> ControllerModel:
    return ControllerModel()

@pytest.fixture
def vm_controller(model_controller: ControllerModel) -> ControllerViewModel:
    return ControllerViewModel(model_controller)

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 0.0, 0),
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 0.5, 1),
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 1.0, 0),
    ],
    ids=[
        "constraint_min: min == val",
        "constraint_min: min < val < max",
        "constraint_min: val == max",
    ]
)
def test_min_value_with_verification_changed(
        model_controller: ControllerModel,
        vm_controller: ControllerViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_controller, attribute_min, init_min)
    setattr(model_controller, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_controller, signal))

    setattr(vm_controller, attribute_min, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_controller, attribute_min) == getattr(model_controller, attribute_min)

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 0.0, 0),
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 0.5, 1),
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 1.0, 0),
    ],
    ids=[
        "constraint_max: min == val",
        "constraint_max: min < val < max",
        "constraint_max: val == max",
    ]
)
def test_max_value_with_verification_changed(
        model_controller: ControllerModel,
        vm_controller: ControllerViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_controller, attribute_min, init_min)
    setattr(model_controller, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_controller, signal))

    setattr(vm_controller, attribute_max, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_controller, attribute_max) == getattr(model_controller, attribute_max)


@pytest.mark.parametrize(
    "attribute, signal, init_value, value",
    [
        ("anti_windup", "antiWindupChanged", AntiWindup.CLAMPING, AntiWindup.CONDITIONAL),
    ],
    ids=[
        "anti_windup",
    ]
)
def test_value_changed(
        model_controller: ControllerModel,
        vm_controller: ControllerViewModel,
        attribute, signal, init_value, value,
        qtbot
) -> None:
    setattr(model_controller, attribute, init_value)

    with qtbot.waitSignal(getattr(vm_controller, signal), timeout=500):
        setattr(vm_controller, attribute, value)

    assert getattr(model_controller, attribute) == getattr(vm_controller, attribute)
