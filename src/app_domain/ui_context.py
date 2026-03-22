from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from viewmodels import LanguageViewModel, ThemeViewModel, SettingsViewModel


@dataclass(frozen=True)
class UiContext:
    settings: SettingsViewModel
    vm_lang: LanguageViewModel
    vm_theme: ThemeViewModel
