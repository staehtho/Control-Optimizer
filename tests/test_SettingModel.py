from models import SettingsModel
from services.controlsys import MySolver

def test_langauge():
    settings = SettingsModel()

    settings.set_language("en")

    assert settings.get_language() == "en"

def test_solver():
    settings = SettingsModel()

    # Über alle Enum-Mitglieder iterieren
    for solver in MySolver:
        settings.set_solver(solver)
        result = settings.get_solver()
        assert result == solver

def test_time_step():
    settings = SettingsModel()

    value = settings.get_time_step()
    settings.set_time_step(value)
    assert settings.get_time_step() == value

def test_pos_particle():
    settings = SettingsModel()

    value = settings.get_pso_particle()
    settings.set_pso_particle(value)
    assert settings.get_pso_particle() == value

def test_pos_iterations():
    settings = SettingsModel()

    value = settings.get_pso_iterations()
    settings.set_pso_iterations(value)
    assert settings.get_pso_iterations() == value

def test_get_qm_file():
    settings = SettingsModel()

    assert settings.get_qm_file("en").name == "app_en.qm"