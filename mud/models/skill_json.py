from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class SkillJson(JsonDataclass):
    """Schema-aligned representation of a skill or spell."""

    name: str
    type: str
    function: str
    target: str = "victim"
    mana_cost: int = 0
    lag: int = 0
    cooldown: int = 0
    failure_rate: float = 0.0
    messages: dict[str, str] = field(default_factory=dict)
