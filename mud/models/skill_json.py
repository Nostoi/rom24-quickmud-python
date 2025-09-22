from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class SkillJson(JsonDataclass):
    """Schema-aligned representation of ROM skills/spells."""

    name: str
    type: str
    function: str
    target: str = "victim"
    mana_cost: int = 0
    lag: int = 0
    cooldown: int = 0
    failure_rate: float = 0.0
    messages: dict[str, str] = field(default_factory=dict)
    rating: dict[str, int] = field(default_factory=dict)
    levels: list[int] = field(default_factory=list)
    ratings: list[int] = field(default_factory=list)
    slot: int = 0
    min_mana: int = 0
    beats: int = 0
