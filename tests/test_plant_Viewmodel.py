from unittest.mock import MagicMock

import numpy as np
import pytest
from PySide6.QtTest import QSignalSpy

from models import ModelContainer
from service import SimulationService
from viewmodels import PlantViewModel


@pytest.fixture
def mock_simulation_service() -> MagicMock:
    service = MagicMock(spec=SimulationService)
    return service


@pytest.fixture
def model_container() -> ModelContainer:
    return ModelContainer()


@pytest.fixture
def plant_vm(model_container: ModelContainer, mock_simulation_service: MagicMock) -> PlantViewModel:
    return PlantViewModel(model_container, mock_simulation_service)


def test_update_num_emits_and_updates_model(plant_vm: PlantViewModel, model_container: ModelContainer) -> None:
    spy = QSignalSpy(plant_vm.numChanged)

    plant_vm.update_num("1, 2")

    assert spy.size() == 1
    assert plant_vm.num == "1, 2"
    assert model_container.model_plant.num == [1.0, 2.0]


def test_update_num_invalid_input_does_not_emit(plant_vm: PlantViewModel, model_container: ModelContainer) -> None:
    spy = QSignalSpy(plant_vm.numChanged)

    plant_vm.update_num("invalid")

    assert spy.size() == 0
    assert plant_vm.num == "invalid"
    assert model_container.model_plant.num == []


def test_update_den_emits_and_updates_model(plant_vm: PlantViewModel, model_container: ModelContainer) -> None:
    spy = QSignalSpy(plant_vm.denChanged)

    plant_vm.update_den("1, 2, 3")

    assert spy.size() == 1
    assert plant_vm.den == "1, 2, 3"
    assert model_container.model_plant.den == [1.0, 2.0, 3.0]


def test_is_valid_changed_emits_when_becoming_valid(plant_vm: PlantViewModel) -> None:
    spy = QSignalSpy(plant_vm.isValidChanged)

    plant_vm.update_num("1")
    plant_vm.update_den("1, 1")

    assert spy.size() == 1
    assert plant_vm.is_valid is True


def test_compute_step_response_calls_service_when_valid(
        model_container: ModelContainer,
        mock_simulation_service: MagicMock,
) -> None:
    model_container.model_plant.num = [1.0]
    model_container.model_plant.den = [1.0, 1.0]
    vm = PlantViewModel(model_container, mock_simulation_service)

    vm.compute_step_response(0.0, 2.0)

    assert mock_simulation_service.compute_plant_response.call_count == 1
    args = mock_simulation_service.compute_plant_response.call_args.args
    assert args[0] is not None


def test_compute_step_response_does_not_call_service_when_invalid(
        plant_vm: PlantViewModel,
        mock_simulation_service: MagicMock,
) -> None:
    plant_vm.compute_step_response(0.0, 2.0)

    assert mock_simulation_service.compute_plant_response.call_count == 0


def test_on_result_emits_step_response_changed(plant_vm: PlantViewModel) -> None:
    spy = QSignalSpy(plant_vm.stepResponseChanged)
    t = np.array([0.0, 1.0])
    y = np.array([0.0, 1.0])

    plant_vm._on_result(t, y)

    assert spy.size() == 1
