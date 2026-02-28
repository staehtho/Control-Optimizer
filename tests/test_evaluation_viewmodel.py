import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtCore import Signal, QObject

from app_domain import PsoResult
from models import EvaluationModel
from viewmodels import EvaluationViewModel


class DummyVm(QObject):
    psoSimulationFinished = Signal()

    def __init__(self):
        super().__init__()
        self._result = None

    def set_pso_result(self, result: PsoResult) -> None:
        self._result = result

    def get_pso_result(self) -> PsoResult:
        return self._result


@pytest.fixture
def model_evaluator() -> EvaluationModel:
    return EvaluationModel()


@pytest.fixture
def vm_evaluator(model_evaluator) -> EvaluationViewModel:
    vm_dummy = DummyVm()
    return EvaluationViewModel(model_evaluator, vm_dummy)


@pytest.mark.parametrize(
    "attribute, signal, init_value, value, spy_size",
    [
        ("kp", "kpChanged", 0, 10, 1),
        ("kp", "kpChanged", 0, 0, 0),
        ("ti", "tiChanged", 0, 10, 1),
        ("ti", "tiChanged", 0, 0, 0),
        ("td", "tdChanged", 0, 10, 1),
        ("td", "tdChanged", 0, 0, 0),
        ("tf", "tfChanged", 0, 10, 1),
        ("tf", "tfChanged", 0, 0, 0),

    ],
    ids=[
        "kp value changed",
        "kp value not changed",
        "ti value changed",
        "ti value not changed",
        "td value changed",
        "td value not changed",
        "tf value changed",
        "tf value not changed",
    ]
)
def test_value_changed(model_evaluator: EvaluationModel, vm_evaluator: EvaluationViewModel,
                       attribute, signal, init_value, value, spy_size) -> None:
    setattr(model_evaluator, attribute, init_value)

    spy = QSignalSpy(getattr(vm_evaluator, signal))

    setattr(vm_evaluator, attribute, value)

    assert getattr(model_evaluator, attribute) == getattr(vm_evaluator, attribute)
    assert spy.size() == spy_size


def test_on_pso_simulation_finished(vm_evaluator: EvaluationViewModel):
    vm_evaluator._vm_pso.set_pso_result(PsoResult(0, 10, 5, 1, 0.1))

    vm_evaluator._vm_pso.psoSimulationFinished.emit()

    assert vm_evaluator.kp == 10
    assert vm_evaluator.ti == 5
    assert vm_evaluator.td == 1
    assert vm_evaluator.tf == 0.1
