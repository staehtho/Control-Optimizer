import numpy as np
from PySide6.QtTest import QSignalSpy

from viewmodels import PlotViewModel
from viewmodels.types import PlotData


def test_grid_changed_emits_once_on_change() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.gridChanged)

    vm.grid = False

    assert spy.size() == 1
    assert vm.grid is False


def test_grid_changed_does_not_emit_on_same_value() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.gridChanged)

    vm.grid = vm.grid

    assert spy.size() == 0


def test_x_min_changed_emits_for_valid_value() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.xMinChanged)

    vm.x_min = 2.0

    assert spy.size() == 1
    assert vm.x_min == 2.0


def test_x_min_rejects_invalid_value() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.xMinChanged)

    vm.x_min = vm.x_max

    assert spy.size() == 0
    assert vm.x_min == 0.0


def test_x_max_changed_emits_for_valid_value() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.xMaxChanged)

    vm.x_max = 20.0

    assert spy.size() == 1
    assert vm.x_max == 20.0


def test_x_max_rejects_invalid_value() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.xMaxChanged)

    vm.x_max = vm.x_min

    assert spy.size() == 0
    assert vm.x_max == 10.0


def test_update_data_emits_only_for_new_or_changed_data() -> None:
    vm = PlotViewModel()
    spy = QSignalSpy(vm.dataChanged)

    vm.update_data(PlotData(key="series", label="series", x=[0.0, 1.0], y=[1.0, 2.0], plot_style=None))
    vm.update_data(PlotData(key="series", label="series", x=[0.0, 1.0], y=[1.0, 2.0], plot_style=None))  # unchanged
    vm.update_data(PlotData(key="series", label="series", x=[0.0, 1.0], y=[1.0, 3.0], plot_style=None))  # changed

    assert spy.size() == 2

    data = vm.get_data()["series"]
    assert np.array_equal(data.x, np.array([0.0, 1.0]))
    assert np.array_equal(data.y, np.array([1.0, 3.0]))


def test_remove_and_clear_data_emit() -> None:
    vm = PlotViewModel()
    vm.update_data(PlotData(key="a", label="a", x=[0.0, 1.0], y=[1.0, 2.0], plot_style=None))
    vm.update_data(PlotData(key="b", label="b", x=[0.0, 1.0], y=[1.0, 2.0], plot_style=None))

    spy_remove = QSignalSpy(vm.dataChanged)
    vm.remove_data("a")

    assert spy_remove.size() == 1
    assert "a" not in vm.get_data()

    spy_clear = QSignalSpy(vm.dataChanged)
    vm.clear_data()

    assert spy_clear.size() == 1
    assert vm.get_data() == {}
