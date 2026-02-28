from unittest.mock import MagicMock

import pytest
from PySide6.QtTest import QSignalSpy

from app_domain.functions import FunctionTypes, SineFunction
from models import FunctionModel
from service import SimulationService
from viewmodels import FunctionViewModel


@pytest.fixture
def mock_simulation_service() -> MagicMock:
    service = MagicMock(spec=SimulationService)
    service.compute_function.return_value = None
    return service


@pytest.fixture
def model() -> FunctionModel:
    return FunctionModel(SineFunction())


@pytest.fixture
def vm(model: FunctionModel, mock_simulation_service: MagicMock) -> FunctionViewModel:
    return FunctionViewModel(model, mock_simulation_service)


def test_set_selected_function_emits_and_updates(vm: FunctionViewModel, qtbot) -> None:
    with qtbot.waitSignal(vm.functionChanged, timeout=200):
        vm.set_selected_function(FunctionTypes.STEP)

    assert vm.selected_function.get_formula() == FunctionTypes.STEP.value().get_formula()


def test_set_selected_function_same_type_does_not_emit(vm: FunctionViewModel) -> None:
    spy = QSignalSpy(vm.functionChanged)

    vm.set_selected_function(FunctionTypes.SINE)

    assert spy.size() == 0


def test_update_param_value_emits_and_updates(vm: FunctionViewModel) -> None:
    spy = QSignalSpy(vm.parameterChanged)
    key = r"A"
    old_value = vm.selected_function.get_param_value(key)
    new_value = old_value + 1.0

    vm.update_param_value(key, new_value)

    assert spy.size() == 1
    assert vm.selected_function.get_param_value(key) == new_value


def test_update_param_value_same_value_does_not_emit(vm: FunctionViewModel) -> None:
    spy = QSignalSpy(vm.parameterChanged)
    key = r"A"
    same_value = vm.selected_function.get_param_value(key)

    vm.update_param_value(key, same_value)

    assert spy.size() == 0


def test_compute_function_delegates_to_service(vm: FunctionViewModel, mock_simulation_service: MagicMock) -> None:
    vm.compute_function(0.0, 1.0)

    assert mock_simulation_service.compute_function.call_count == 1
    t, func, callback = mock_simulation_service.compute_function.call_args.args
    assert len(t) == 5000
    assert callable(func)
    assert callable(callback)


def test_compute_finished_signal_is_emitted_from_callback(
        vm: FunctionViewModel,
        mock_simulation_service: MagicMock,
) -> None:
    spy = QSignalSpy(vm.computeFinished)

    vm.compute_function(0.0, 1.0)

    t, _, callback = mock_simulation_service.compute_function.call_args.args
    y = vm.selected_function.get_function()(t)
    callback(t, y)

    assert spy.size() == 1
