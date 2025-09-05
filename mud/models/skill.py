from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .skill_json import SkillJson


@dataclass
class Skill:
    """Runtime representation of a skill or spell."""

    name: str
    type: str
    function: str
    target: str = "victim"
    mana_cost: int = 0
    lag: int = 0
    cooldown: int = 0
    failure_rate: float = 0.0
    messages: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: SkillJson) -> "Skill":
        return cls(**data.to_dict())
