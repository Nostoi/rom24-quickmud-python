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
    rating: Dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: SkillJson) -> "Skill":
        payload = data.to_dict()
        raw_rating = payload.pop("rating", {}) or {}
        converted_rating: Dict[int, int] = {}
        for key, value in raw_rating.items():
            try:
                converted_rating[int(key)] = int(value)
            except (TypeError, ValueError):
                continue
        return cls(rating=converted_rating, **payload)
