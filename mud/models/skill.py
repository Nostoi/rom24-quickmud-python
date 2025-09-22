from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

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
<<<<<<< HEAD
    rating: Dict[int, int] = field(default_factory=dict)
=======
    # ROM metadata (const.c:skill_table)
    levels: Tuple[int, int, int, int] = (99, 99, 99, 99)
    ratings: Tuple[int, int, int, int] = (0, 0, 0, 0)
    slot: int = 0
    min_mana: int = 0
    beats: int = 0
>>>>>>> d64de0a (Many significant changes)

    @classmethod
    def from_json(cls, data: SkillJson) -> "Skill":
        payload = data.to_dict()
<<<<<<< HEAD
        raw_rating = payload.pop("rating", {}) or {}
        converted_rating: Dict[int, int] = {}
        for key, value in raw_rating.items():
            try:
                converted_rating[int(key)] = int(value)
            except (TypeError, ValueError):
                continue
        return cls(rating=converted_rating, **payload)
=======
        levels = payload.get("levels")
        if levels:
            payload["levels"] = tuple(int(v) for v in levels)
        else:
            payload.pop("levels", None)
        ratings = payload.get("ratings")
        if ratings:
            payload["ratings"] = tuple(int(v) for v in ratings)
        else:
            payload.pop("ratings", None)
        return cls(**payload)
>>>>>>> d64de0a (Many significant changes)
