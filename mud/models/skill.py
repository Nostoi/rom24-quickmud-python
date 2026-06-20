from __future__ import annotations

from dataclasses import dataclass, field

from mud.models.constants import Position

from .skill_json import SkillJson


@dataclass
class Skill:
    """Runtime representation of a ROM skill/spell entry."""

    name: str
    type: str
    function: str
    target: str = "victim"
    mana_cost: int = 0
    lag: int = 0
    cooldown: int = 0
    failure_rate: float = 0.0
    messages: dict[str, str] = field(default_factory=dict)
    # Legacy ROM `rating` lookup keyed by class index (act_info.c)
    rating: dict[int, int] = field(default_factory=dict)
    # ROM metadata extracted from const.c for modern callers
    levels: tuple[int, int, int, int] = (99, 99, 99, 99)
    ratings: tuple[int, int, int, int] = (0, 0, 0, 0)
    slot: int = 0
    min_mana: int = 0
    beats: int = 0
    # ROM skill_table minimum_position (src/merc.h:1951, "Position for caster").
    # do_cast gates on this per spell (src/magic.c:341). Default FIGHTING is the
    # safe backstop (CAST-013): identical to the historical flat gate, so an
    # unmapped spell can never regress an offensive cast — only a mapped
    # POS_STANDING spell newly blocks while fighting. registry.load overwrites
    # it from const.c via ROM_SKILL_MIN_POSITION.
    minimum_position: Position = Position.FIGHTING

    @classmethod
    def from_json(cls, data: SkillJson) -> Skill:
        payload = data.to_dict()

        raw_rating = payload.pop("rating", {}) or {}
        converted_rating: dict[int, int] = {}
        for key, value in raw_rating.items():
            try:
                converted_rating[int(key)] = int(value)
            except (TypeError, ValueError):
                continue

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

        return cls(rating=converted_rating, **payload)
