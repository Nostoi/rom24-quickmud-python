from __future__ import annotations

import builtins
from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class ResourceJson(JsonDataclass):
    """Track current and maximum resource values."""

    current: int
    max: int


@dataclass
class StatsJson(JsonDataclass):
    """Primary stats and pooled resources."""

    str: int
    int: int
    wis: builtins.int
    dex: builtins.int
    con: builtins.int
    hitpoints: ResourceJson
    mana: ResourceJson
    move: ResourceJson


@dataclass
class CharacterJson(JsonDataclass):
    """Character record matching ``schemas/character.schema.json``."""

    id: int
    name: str
    description: str
    level: int
    stats: StatsJson
    position: str
    short_description: str | None = None
    long_description: str | None = None
    alignment: int = 0
    gold: int = 0
    silver: int = 0
    skills: dict[str, int] = field(default_factory=dict)
    inventory: list[int] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
