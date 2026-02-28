from app_domain.controlsys import MySolver
from models import SettingsModel


def test_language_roundtrip() -> None:
    settings = SettingsModel()

    settings.set_language("en")

    assert settings.get_language() == "en"


def test_solver_roundtrip_for_all_enum_values() -> None:
    settings = SettingsModel()

    for solver in MySolver:
        settings.set_solver(solver)
        assert settings.get_solver() == solver


def test_time_step_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.get_time_step()
    settings.set_time_step(value)

    assert settings.get_time_step() == value


def test_pso_particle_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.get_pso_particle()
    settings.set_pso_particle(value)

    assert settings.get_pso_particle() == value


def test_pso_iterations_roundtrip() -> None:
    settings = SettingsModel()

    value = settings.get_pso_iterations()
    settings.set_pso_iterations(value)

    assert settings.get_pso_iterations() == value


def test_get_qm_file_for_en() -> None:
    settings = SettingsModel()

    assert settings.get_qm_file("en").name == "app_en.qm"
