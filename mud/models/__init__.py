"""Data models for QuickMUD translated from C structs."""

from .area import Area
from .area_json import AreaJson, VnumRangeJson
from .board import Board
from .board_json import BoardJson
from .character import Character, PCData
from .character_json import CharacterJson, ResourceJson, StatsJson
from .constants import (
    ActFlag,
    Direction,
    ItemType,
    Position,
    Sector,
    Sex,
    Size,
    Stat,
    WearLocation,
)
from .help import HelpEntry
from .help_json import HelpJson
from .json_io import (
    JsonDataclass,
    dataclass_from_dict,
    dataclass_to_dict,
    dump_dataclass,
    load_dataclass,
)
from .mob import MobIndex, MobProgram
from .note import Note
from .note_json import NoteJson
from .obj import Affect, ObjectData, ObjIndex
from .object import Object
from .object_json import (
    AffectJson as ObjectAffectJson,
)
from .object_json import (
    ExtraDescriptionJson as ObjectExtraDescriptionJson,
)
from .object_json import (
    ObjectJson,
)
from .player_json import PlayerJson
from .room import Exit, ExtraDescr, Room
from .room_json import (
    ExitJson,
    ResetJson,
    RoomJson,
)
from .room_json import (
    ExtraDescriptionJson as RoomExtraDescriptionJson,
)
from .room_json import ResetJson as Reset
from .shop import Shop
from .shop_json import ShopJson
from .skill import Skill
from .skill_json import SkillJson
from .social import Social
from .social_json import SocialJson

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
    "Stat",
    "WearLocation",
    "Sex",
    "Size",
    "ItemType",
    "ActFlag",
]
