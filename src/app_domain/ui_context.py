from dataclasses import dataclass

from viewmodels import LanguageViewModel, ThemeViewModel, SettingsViewModel


@dataclass(frozen=True)
class UiContext:
    settings: SettingsViewModel
    vm_lang: LanguageViewModel
    vm_theme: ThemeViewModel
