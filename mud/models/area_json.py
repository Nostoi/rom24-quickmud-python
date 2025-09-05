from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .room_json import RoomJson
from .character_json import CharacterJson
from .object_json import ObjectJson
from .json_io import JsonDataclass


@dataclass
class VnumRangeJson(JsonDataclass):
    """Minimum and maximum vnums for an area."""
    min: int
    max: int


@dataclass
class AreaJson(JsonDataclass):
    """Area record matching ``schemas/area.schema.json``."""
    name: str
    vnum_range: VnumRangeJson
    builders: List[str] = field(default_factory=list)
    rooms: List[RoomJson] = field(default_factory=list)
    mobiles: List[CharacterJson] = field(default_factory=list)
    objects: List[ObjectJson] = field(default_factory=list)
