from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.area import Area
    from mud.models.character import Character
    from mud.models.object import Object
    from mud.spawning.templates import MobInstance

from .constants import Direction
from .room_json import ResetJson


@dataclass
class ExtraDescr:
    """Python representation of EXTRA_DESCR_DATA"""

    keyword: str | None = None
    description: str | None = None


@dataclass
class Exit:
    """Representation of EXIT_DATA"""

    to_room: Room | None = None
    vnum: int | None = None
    exit_info: int = 0
    key: int = 0
    keyword: str | None = None
    description: str | None = None
    flags: str = "0"  # String representation of exit flags
    rs_flags: int = 0
    orig_door: int = 0


@dataclass
class Room:
    """Runtime room container built from area files."""

    vnum: int
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    area: Area | None = None
    room_flags: int = 0
    light: int = 0
    sector_type: int = 0
    heal_rate: int = 100
    mana_rate: int = 100
    clan: int = 0
    exits: list[Exit | None] = field(default_factory=lambda: [None] * len(Direction))
    extra_descr: list[ExtraDescr] = field(default_factory=list)
    resets: list[ResetJson] = field(default_factory=list)
    people: list[Character] = field(default_factory=list)
    contents: list[Object] = field(default_factory=list)
    next: Room | None = None

    def __repr__(self) -> str:
        return f"<Room vnum={self.vnum} name={self.name!r}>"

    def add_character(self, char: Character) -> None:
        already_present = char in self.people
        if not already_present:
            self.people.append(char)
        char.room = self

        area = getattr(self, "area", None)
        if not already_present and area is not None and not getattr(char, "is_npc", True):
            if getattr(area, "empty", False):
                area.empty = False
                area.age = 0
            area.nplayer = int(getattr(area, "nplayer", 0)) + 1

    def remove_character(self, char: Character) -> None:
        if char in self.people:
            self.people.remove(char)
            area = getattr(self, "area", None)
            if area is not None and not getattr(char, "is_npc", True):
                current = int(getattr(area, "nplayer", 0))
                area.nplayer = max(0, current - 1)
        if getattr(char, "room", None) is self:
            char.room = None

    def add_object(self, obj: Object) -> None:
        if obj not in self.contents:
            self.contents.append(obj)
        if hasattr(obj, "location"):
            obj.location = self

    def add_mob(self, mob: MobInstance) -> None:
        if mob not in self.people:
            self.people.append(mob)
        mob.room = self

    def broadcast(self, message: str, exclude: Character | None = None) -> None:
        for char in self.people:
            if char is exclude:
                continue
            if hasattr(char, "messages"):
                char.messages.append(message)


room_registry: dict[int, Room] = {}
