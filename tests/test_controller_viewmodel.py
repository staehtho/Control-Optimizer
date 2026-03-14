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


def test_controller_type_emits_on_change(vm_controller: ControllerViewModel) -> None:
    spy = QSignalSpy(vm_controller.controllerTypeChanged)

    vm_controller.controller_type = "PI"

    assert spy.size() == 1
    assert vm_controller.controller_type == "PI"


@pytest.mark.parametrize(
    ("value", "expected", "expected_signal_count"),
    [
        (0.5, 0.5, 1),  # valid update
        (1.0, -5.0, 0),  # invalid (equal to max)
    ],
)
def test_constraint_min_validation_and_signal_behavior(
        vm_controller: ControllerViewModel,
        value: float,
        expected: float,
        expected_signal_count: int,
) -> None:
    vm_controller.constraint_min = -5.0
    vm_controller.constraint_max = 1.0

    spy = QSignalSpy(vm_controller.constraintMinChanged)
    vm_controller.constraint_min = value

    assert spy.size() == expected_signal_count
    assert vm_controller.constraint_min == expected


@pytest.mark.parametrize(
    ("value", "expected", "expected_signal_count"),
    [
        (0.5, 0.5, 1),  # valid update
        (0.0, 5.0, 0),  # invalid (equal to min)
    ],
)
def test_constraint_max_validation_and_signal_behavior(
        vm_controller: ControllerViewModel,
        value: float,
        expected: float,
        expected_signal_count: int,
) -> None:
    vm_controller.constraint_min = 0.0
    vm_controller.constraint_max = 5.0

    spy = QSignalSpy(vm_controller.constraintMaxChanged)
    vm_controller.constraint_max = value

    assert spy.size() == expected_signal_count
    assert vm_controller.constraint_max == expected


def test_anti_windup_emits_and_updates(vm_controller: ControllerViewModel, qtbot) -> None:
    with qtbot.waitSignal(vm_controller.antiWindupChanged, timeout=500):
        vm_controller.anti_windup = AntiWindup.CONDITIONAL

    assert vm_controller.anti_windup == AntiWindup.CONDITIONAL
