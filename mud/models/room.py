from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.object import Object
    from mud.spawning.templates import MobInstance
    from mud.models.area import Area
    from mud.models.character import Character

from .constants import Direction
from .room_json import ResetJson

@dataclass
class ExtraDescr:
    """Python representation of EXTRA_DESCR_DATA"""
    keyword: Optional[str] = None
    description: Optional[str] = None

@dataclass
class Exit:
    """Representation of EXIT_DATA"""
    to_room: Optional['Room'] = None
    vnum: Optional[int] = None
    exit_info: int = 0
    key: int = 0
    keyword: Optional[str] = None
    description: Optional[str] = None
    flags: str = '0'  # String representation of exit flags
    rs_flags: int = 0
    orig_door: int = 0

@dataclass
class Room:
    """Runtime room container built from area files."""
    vnum: int
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    area: Optional['Area'] = None
    room_flags: int = 0
    light: int = 0
    sector_type: int = 0
    heal_rate: int = 0
    mana_rate: int = 0
    clan: int = 0
    exits: List[Optional[Exit]] = field(default_factory=lambda: [None] * len(Direction))
    extra_descr: List[ExtraDescr] = field(default_factory=list)
    resets: List[ResetJson] = field(default_factory=list)
    people: List['Character'] = field(default_factory=list)
    contents: List['Object'] = field(default_factory=list)
    next: Optional['Room'] = None

    def __repr__(self) -> str:
        return f"<Room vnum={self.vnum} name={self.name!r}>"

    def add_character(self, char: 'Character') -> None:
        if char not in self.people:
            self.people.append(char)
        char.room = self

    def remove_character(self, char: 'Character') -> None:
        if char in self.people:
            self.people.remove(char)

    def add_object(self, obj: 'Object') -> None:
        if obj not in self.contents:
            self.contents.append(obj)
        if hasattr(obj, "location"):
            obj.location = self

    def add_mob(self, mob: 'MobInstance') -> None:
        if mob not in self.people:
            self.people.append(mob)
        mob.room = self

    def broadcast(self, message: str, exclude: Optional['Character'] = None) -> None:
        for char in self.people:
            if char is exclude:
                continue
            if hasattr(char, 'messages'):
                char.messages.append(message)


room_registry: dict[int, Room] = {}

