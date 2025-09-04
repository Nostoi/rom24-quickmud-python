from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Callable, Dict

from mud.models import SkillJson
from mud.models.json_io import dataclass_from_dict

skill_registry: Dict[str, Callable] = {}


def load_skills(path: Path) -> None:
    """Load skill definitions from JSON and register their handlers."""
    with path.open() as fp:
        data = json.load(fp)
    for entry in data:
        skill = dataclass_from_dict(SkillJson, entry)
        module = import_module("mud.skills.handlers")
        func = getattr(module, skill.function)
        skill_registry[skill.name] = func
