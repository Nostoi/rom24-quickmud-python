"""Data models for QuickMUD translated from C structs."""

from .area import Area
from .room import Room, ExtraDescr, Exit
from .room_json import ResetJson as Reset
from .mob import MobIndex, MobProgram
from .obj import ObjIndex, ObjectData, Affect
from .object import Object
from .character import Character, PCData
from .shop import Shop
from .skill import Skill
from .help import HelpEntry
from .social import Social
from .board import Board
from .note import Note
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
from .player_json import PlayerJson
from .skill_json import SkillJson
from .shop_json import ShopJson
from .help_json import HelpJson
from .social_json import SocialJson
from .board_json import BoardJson
from .note_json import NoteJson
from .json_io import (
    JsonDataclass,
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
    "Shop",
    "Skill",
    "HelpEntry",
    "Social",
    "Board",
    "Note",
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
    "PlayerJson",
    "SkillJson",
    "ShopJson",
    "HelpJson",
    "SocialJson",
    "BoardJson",
    "NoteJson",
    "JsonDataclass",
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
