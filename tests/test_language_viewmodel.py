import pytest
from PySide6.QtTest import QSignalSpy

from models import SettingsModel
from viewmodels import LanguageViewModel

@pytest.fixture
def settings_model() -> SettingsModel:
    return SettingsModel()

@pytest.fixture
def lang_vm(settings_model: SettingsModel) -> LanguageViewModel:
    return LanguageViewModel(settings_model)


@pytest.mark.parametrize(
    "lang_code",
    [
        "de",
        "en",
    ],
)
def test_language_change_persists_and_emits_once(
        settings_model: SettingsModel,
        lang_vm: LanguageViewModel,
        lang_code: str,
        qtbot,
) -> None:
    lang_vm._current_lang = ""

    with qtbot.waitSignal(lang_vm.languageChanged, timeout=100):
        lang_vm.set_language(lang_code)

    assert lang_vm.current_language == lang_code
    assert settings_model.get_language() == lang_code


def test_language_change_same_value_does_not_emit(lang_vm: LanguageViewModel) -> None:
    current = lang_vm.current_language
    spy = QSignalSpy(lang_vm.languageChanged)

    lang_vm.set_language(current)

    assert spy.size() == 0


def test_get_lang_cfg_contains_required_keys(lang_vm: LanguageViewModel) -> None:
    cfg = lang_vm.get_lang_cfg()

    assert "en" in cfg
    assert "de" in cfg
    assert "qm" in cfg["en"]
