from __future__ import annotations

from dataclasses import dataclass, field

from .character_json import CharacterJson
from .json_io import JsonDataclass
from .object_json import ObjectJson
from .room_json import RoomJson


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
    builders: list[str] = field(default_factory=list)
    rooms: list[RoomJson] = field(default_factory=list)
    mobiles: list[CharacterJson] = field(default_factory=list)
    objects: list[ObjectJson] = field(default_factory=list)
