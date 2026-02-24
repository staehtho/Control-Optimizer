import pytest
from PySide6.QtTest import QSignalSpy

from app_domain.controlsys import PerformanceIndex, AntiWindup, ExcitationTarget
from models import ModelContainer
from viewmodels import PsoConfigurationViewModel

@pytest.fixture
def model_container() -> ModelContainer:
    return ModelContainer()

@pytest.fixture
def vm_pso(model_container: ModelContainer) -> PsoConfigurationViewModel:
    return PsoConfigurationViewModel(model_container)

def test_plant_changed(model_container: ModelContainer, vm_pso: PsoConfigurationViewModel, qtbot) -> None:
    model_container.model_plant.num= [1]
    model_container.model_plant.den = [1, 1]

    with qtbot.waitSignal(vm_pso.plantChanged, timeout=500):
        model_container.model_plant.num = [2]
        model_container.model_plant.den = [1, 1, 1]

    assert vm_pso.get_plant_num_den() == ([2], [1, 1, 1])

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("start_time", "end_time", "startTimeChanged", 0, 1, 0.0, 0),
        ("start_time", "end_time", "startTimeChanged", 0, 1, 0.5, 1),
        ("start_time", "end_time", "startTimeChanged", 0, 1, 1.0, 0),
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 0.0, 0),
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 0.5, 1),
        ("constraint_min", "constraint_max", "constraintMinChanged", 0, 1, 1.0, 0),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 0.0, 0),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 0.5, 1),
        ("kp_min", "kp_max", "kpMinChanged", 0, 1, 1.0, 0),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 0.0, 0),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 0.5, 1),
        ("ti_min", "ti_max", "tiMinChanged", 0, 1, 1.0, 0),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 0.0, 0),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 0.5, 1),
        ("td_min", "td_max", "tdMinChanged", 0, 1, 1.0, 0)
    ],
    ids=[
        "start_time: min == val",
        "start_time: min < val < max",
        "start_time: val == max",
        "constraint_min: min == val",
        "constraint_min: min < val < max",
        "constraint_min: val == max",
        "kp_min: min == val",
        "kp_min: min < val < max",
        "kp_min: val == max",
        "ti_min: min == val",
        "ti_min: min < val < max",
        "ti_min: val == max",
        "td_min: min == val",
        "td_min: min < val < max",
        "td_min: val == max",
    ]
)
def test_min_value_with_verification_changed(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_container.model_pso, attribute_min, init_min)
    setattr(model_container.model_pso, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_pso, signal))

    setattr(vm_pso, attribute_min, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_pso, attribute_min) == getattr(model_container.model_pso, attribute_min)

@pytest.mark.parametrize(
    "attribute_min, attribute_max, signal, init_min, init_max, value, expected_spy_size",
    [
        ("start_time", "end_time", "endTimeChanged", 0, 1, 0.0, 0),
        ("start_time", "end_time", "endTimeChanged", 0, 1, 0.5, 1),
        ("start_time", "end_time", "endTimeChanged", 0, 1, 1.0, 0),
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 0.0, 0),
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 0.5, 1),
        ("constraint_min", "constraint_max", "constraintMaxChanged", 0, 1, 1.0, 0),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 0.0, 0),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 0.5, 1),
        ("kp_min", "kp_max", "kpMaxChanged", 0, 1, 1.0, 0),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 0.0, 0),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 0.5, 1),
        ("ti_min", "ti_max", "tiMaxChanged", 0, 1, 1.0, 0),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 0.0, 0),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 0.5, 1),
        ("td_min", "td_max", "tdMaxChanged", 0, 1, 1.0, 0)
    ],
    ids=[
        "end_time: min == val",
        "end_time: min < val < max",
        "end_time: val == max",
        "constraint_max: min == val",
        "constraint_max: min < val < max",
        "constraint_max: val == max",
        "kp_max: min == val",
        "kp_max: min < val < max",
        "kp_max: val == max",
        "ti_max: min == val",
        "ti_max: min < val < max",
        "ti_max: val == max",
        "td_max: min == val",
        "td_max: min < val < max",
        "td_max: val == max",
    ]
)
def test_max_value_with_verification_changed(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute_min, attribute_max, signal,
        init_min, init_max, value, expected_spy_size
) -> None:
    setattr(model_container.model_pso, attribute_min, init_min)
    setattr(model_container.model_pso, attribute_max, init_max)

    spy = QSignalSpy(getattr(vm_pso, signal))

    setattr(vm_pso, attribute_max, value)

    assert spy.size() == expected_spy_size
    assert getattr(vm_pso, attribute_max) == getattr(model_container.model_pso, attribute_max)


@pytest.mark.parametrize(
    "attribute, signal, init_value, value",
    [
        ("anti_windup", "antiWindupChanged", AntiWindup.CLAMPING, AntiWindup.CONDITIONAL),
        ("excitation_target", "excitationTargetChanged", ExcitationTarget.REFERENCE,
         ExcitationTarget.INPUT_DISTURBANCE),
        ("performance_index", "performanceIndexChanged", PerformanceIndex.ITAE, PerformanceIndex.IAE)
    ],
    ids=[
        "anti_windup",
        "excitation_target",
        "performance_index",
    ]
)
def test_value_changed(
        model_container: ModelContainer,
        vm_pso: PsoConfigurationViewModel,
        attribute, signal, init_value, value,
        qtbot
) -> None:
    setattr(model_container.model_pso, attribute, init_value)

    with qtbot.waitSignal(getattr(vm_pso, signal), timeout=500):
        setattr(vm_pso, attribute, value)

    assert getattr(model_container.model_pso, attribute) == getattr(vm_pso, attribute)
