from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication

from app_domain.functions import FunctionTypes, SineFunction
from models import FunctionModel
from service import SimulationService
from viewmodels import FunctionViewModel


@pytest.fixture
def qt_app():
    """Stellt sicher, dass ein QCoreApplication existiert für PySide6 Signals."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app

@pytest.fixture
def mock_simulation_service():
    service = MagicMock(spec=SimulationService)
    # Optional: definiere, was compute oder andere Methoden zurückgeben sollen
    service.compute_function.return_value = None
    return service

@pytest.fixture
def model() -> FunctionModel:
    return FunctionModel(SineFunction())

@pytest.fixture
def vm(model: FunctionModel, mock_simulation_service) -> FunctionViewModel:
    return FunctionViewModel(model, mock_simulation_service)

def test_function_change(model, vm, qtbot):

    model._selected_function = SineFunction()

    with qtbot.waitSignal(vm.functionChanged, timeout=100):
        vm.set_selected_function(FunctionTypes.STEP)

    assert vm.selected_function.get_formula() == FunctionTypes.STEP.value().get_formula()

def test_compute_finished_signal(qt_app, model, mock_simulation_service):
    vm = FunctionViewModel(model_function=model, simulation_service=mock_simulation_service)

    # Spy für Signal
    captured = {}
    def on_finished(t, y):
        captured['t'] = t
        captured['y'] = y

    vm.computeFinished.connect(on_finished)

    # Mocked compute_function ruft Callback sofort auf
    def fake_compute_function(t, func, callback):
        y = func(t)
        callback(t, y)

    mock_simulation_service.compute_function.side_effect = fake_compute_function

    # Aufruf der Methode
    vm.compute_function(0, 1)

    # Prüfen, dass Signal gefeuert wurde
    assert 't' in captured
    assert 'y' in captured