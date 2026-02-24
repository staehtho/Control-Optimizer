import pytest

from models import SettingsModel
from viewmodels import LanguageViewModel

@pytest.fixture
def settings_model() -> SettingsModel:
    return SettingsModel()

@pytest.fixture
def lang_vm(settings_model: SettingsModel) -> LanguageViewModel:
    return LanguageViewModel(settings_model)

@pytest.mark.parametrize(
    "lang",
    [
        "de",
        "en"
    ]
)
def test_language_change(settings_model, lang_vm: LanguageViewModel, lang, qtbot):
    lang_vm._current_lang = ""

    with qtbot.waitSignal(lang_vm.languageChanged, timeout=100):
        lang_vm.set_language(lang)

    assert lang_vm.current_language == lang
    assert settings_model.get_language() == lang
    assert lang in lang_vm._translator.language()