from viewmodels import PlotViewModel

def test_grid_changed(qtbot):
    vm = PlotViewModel()
    vm._grid = False

    with qtbot.waitSignal(vm.gridChanged, timeout=100):
        vm.grid = True

    assert vm.grid

def test_start_time_changed(qtbot):
    vm = PlotViewModel()
    vm._start_time = 0

    with qtbot.waitSignal(vm.startTimeChanged, timeout=100):
        vm.start_time = 5

    assert vm.start_time == 5


def test_end_time_changed(qtbot):
    vm = PlotViewModel()
    vm._end_time = 0

    with qtbot.waitSignal(vm.endTimeChanged, timeout=100):
        vm.end_time = 100

    assert vm.end_time == 100

def test_data_changed(qtbot):
    vm = PlotViewModel()
    vm._data = {}

    key = "test"

    with qtbot.waitSignal(vm.dataChanged, timeout=100):
        vm.update_data(key, ([1], [1]))

    assert vm.get_data().get(key) == ([1], [1])