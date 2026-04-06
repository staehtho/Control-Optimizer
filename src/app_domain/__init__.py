from importlib import import_module
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .app_engine import AppEngine
    from .ui_context import UiContext

__all__ = ["AppEngine", "UiContext"]


def __getattr__(name: str) -> Any:
    if name == "AppEngine":
        return import_module(".app_engine", __name__).AppEngine
    if name == "UiContext":
        return import_module(".ui_context", __name__).UiContext
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
