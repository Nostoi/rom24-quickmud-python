"""Data models for QuickMUD translated from C structs."""

from .area import Area
from .room import Room, ExtraDescr, Exit, Reset
from .mob import MobIndex, MobProgram
from .obj import ObjIndex, ObjectData, Affect
from .object import Object
from .character import Character, PCData
from .constants import (
    Direction,
    Sector,
    Position,
    WearLocation,
    Sex,
    Size,
    ItemType,
)

from .area_json import AreaJson, VnumRangeJson
from .room_json import (
    RoomJson,
    ExitJson,
    ExtraDescriptionJson as RoomExtraDescriptionJson,
    ResetJson,
)
from .object_json import (
    ObjectJson,
    AffectJson as ObjectAffectJson,
    ExtraDescriptionJson as ObjectExtraDescriptionJson,
)
from .character_json import CharacterJson, StatsJson, ResourceJson
from .json_io import (
    dataclass_from_dict,
    dataclass_to_dict,
    dump_dataclass,
    load_dataclass,
)

__all__ = [
    "Area",
    "Room",
    "ExtraDescr",
    "Exit",
    "Reset",
    "MobIndex",
    "MobProgram",
    "ObjIndex",
    "ObjectData",
    "Object",
    "Affect",
    "Character",
    "PCData",
    # JSON schema-aligned dataclasses
    "AreaJson",
    "VnumRangeJson",
    "RoomJson",
    "ExitJson",
    "RoomExtraDescriptionJson",
    "ResetJson",
    "ObjectJson",
    "ObjectAffectJson",
    "ObjectExtraDescriptionJson",
    "CharacterJson",
    "StatsJson",
    "ResourceJson",
    "dataclass_from_dict",
    "dataclass_to_dict",
    "load_dataclass",
    "dump_dataclass",
    "Direction",
    "Sector",
    "Position",
    "WearLocation",
    "Sex",
    "Size",
    "ItemType",
]
