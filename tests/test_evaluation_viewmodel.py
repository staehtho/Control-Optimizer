import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtCore import Signal, QObject

from app_domain.engine import PsoResult
from models import EvaluationModel
from viewmodels import EvaluationViewModel


class DummyVm(QObject):
    psoSimulationFinished = Signal()

    def __init__(self):
        super().__init__()
        self._result = None

    def set_pso_result(self, result: PsoResult) -> None:
        self._result = result

    def get_pso_result(self) -> PsoResult | None:
        return self._result


@pytest.fixture
def model_evaluator() -> EvaluationModel:
    return EvaluationModel()


@pytest.fixture
def vm_evaluator(model_evaluator: EvaluationModel) -> EvaluationViewModel:
    vm_dummy = DummyVm()
    return EvaluationViewModel(model_evaluator, vm_dummy)


@pytest.mark.parametrize(
    "attribute, signal, init_value, value, expected_signal_count",
    [
        ("kp", "kpChanged", 0.0, 10.0, 1),
        ("kp", "kpChanged", 0.0, 0.0, 0),
        ("ti", "tiChanged", 0.0, 10.0, 1),
        ("ti", "tiChanged", 0.0, 0.0, 0),
        ("td", "tdChanged", 0.0, 10.0, 1),
        ("td", "tdChanged", 0.0, 0.0, 0),
        ("tf", "tfChanged", 0.0, 10.0, 1),
        ("tf", "tfChanged", 0.0, 0.0, 0),
    ],
)
def test_property_update_emits_only_on_change(
        model_evaluator: EvaluationModel,
        vm_evaluator: EvaluationViewModel,
        attribute: str,
        signal: str,
        init_value: float,
        value: float,
        expected_signal_count: int,
) -> None:
    setattr(model_evaluator, attribute, init_value)

    spy = QSignalSpy(getattr(vm_evaluator, signal))
    setattr(vm_evaluator, attribute, value)

    assert getattr(model_evaluator, attribute) == getattr(vm_evaluator, attribute)
    assert spy.size() == expected_signal_count


def test_pso_finished_populates_all_values(vm_evaluator: EvaluationViewModel) -> None:
    vm_evaluator._vm_pso.set_pso_result(PsoResult(0, 10, 5, 1, 0.1))

    vm_evaluator._vm_pso.psoSimulationFinished.emit()

    assert vm_evaluator.kp == 10
    assert vm_evaluator.ti == 5
    assert vm_evaluator.td == 1
    assert vm_evaluator.tf == 0.1


def test_pso_finished_with_no_result_clears_values(vm_evaluator: EvaluationViewModel) -> None:
    vm_evaluator.kp = 4.0
    vm_evaluator.ti = 3.0
    vm_evaluator.td = 2.0
    vm_evaluator.tf = 1.0

    vm_evaluator._vm_pso.set_pso_result(None)
    vm_evaluator._vm_pso.psoSimulationFinished.emit()

    assert vm_evaluator.kp == 0.0
    assert vm_evaluator.ti == 0.0
    assert vm_evaluator.td == 0.0
    assert vm_evaluator.tf == 0.0
