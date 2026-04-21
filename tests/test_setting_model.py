from app_domain.controlsys import MySolver
from models import SettingsModel


def test_language_roundtrip() -> None:
    settings = SettingsModel()

    settings.set_language("en")

    assert settings.get_language() == "en"


def test_solver_roundtrip_for_all_enum_values() -> None:
    settings = SettingsModel()

    for solver in MySolver:
        settings.solver = solver
        assert settings.solver == solver


def test_time_step_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.time_step
    settings.time_step = value

    assert settings.time_step == value


def test_pso_particle_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.pso_swarm_size
    settings.pso_swarm_size = value

    assert settings.pso_swarm_size == value


def test_pso_iterations_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.pso_repeat_runs
    settings.pso_repeat_runs = value

    assert settings.pso_repeat_runs == value


def test_get_qm_file_for_en() -> None:
    settings = SettingsModel()

    assert settings.get_qm_file("en").name == "app_en.qm"
