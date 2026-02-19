from models import PlantModel

from PySide6.QtTest import QSignalSpy

import pytest

@pytest.mark.parametrize(
    "num",
    [
        ([1, 2, 3, 4]),
        ([1, 2]),
    ]
)
def test_model_num_changed_signal(num,  qtbot):
    model = PlantModel()

    with qtbot.waitSignal(model.numChanged, timeout=100):
        model.num = num

    assert model.num == num

def test_model_num_changed_signal_no_change():
    model = PlantModel()

    spy = QSignalSpy(model.numChanged)

    model.num = []
    assert spy.size() == 0

    model.num = [1, 2]
    assert spy.size() == 1

    model.num = [1, 2]
    assert spy.size() == 1

@pytest.mark.parametrize(
    "den",
    [
        ([1, 2, 3, 4]),
        ([1, 2]),
    ]
)
def test_model_den_changed_signal(den,  qtbot):
    model = PlantModel()

    with qtbot.waitSignal(model.denChanged, timeout=100):
        model.den = den

    assert model.den == den


def test_model_den_changed_signal_no_change():
    model = PlantModel()

    spy = QSignalSpy(model.denChanged)

    model.den = []
    assert spy.size() == 0

    model.den = [1, 2]
    assert spy.size() == 1

    model.den = [1, 2]
    assert spy.size() == 1

@pytest.mark.parametrize(
    "num, den, expected",
    [
        ([1, 2], [1, 2], True),
        ([1, 2], [], False),
        ([], [1, 2], False),
        ([], [], False),
    ]
)
def test_model_is_valid(num, den, expected):
    model = PlantModel()

    spy = QSignalSpy(model.isValidChanged)

    model.num = num

    # nach num noch nicht valid und kein Signal ausgelöst
    assert spy.size() == 0
    assert not model.is_valid()

    model.den = den

    assert spy.size() == (1 if expected else 0)
    assert model.is_valid() is expected

@pytest.mark.parametrize(
    "num, den, expected",
    [
        ([1, 1], [1, 1, 1, 1, 1], True),
        ([1, 1], [], False),
    ]
)
def test_model_plant_num_den_changed(num, den, expected):
    model = PlantModel()

    model.num = num
    model.den = den

    plant = model.get_plant()
    if expected:
        # Länge muss übereinstimmen, wenn beide model.is_valid
        assert model.is_valid()
        assert len(list(plant.num)) == len(num)
        assert len(list(plant.den)) == len(den)
    else:
        assert not model.is_valid()
        assert len(list(plant.num)) != len(num) or len(list(plant.den)) != len(den)

