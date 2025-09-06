from __future__ import annotations
from typing import Callable, Dict, Any

spec_fun_registry: Dict[str, Callable[..., Any]] = {}

def register_spec_fun(name: str, func: Callable[..., Any]) -> None:
    spec_fun_registry[name] = func
