from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from mud.models.object import Object

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.mob import MobIndex
    from mud.models.obj import ObjIndex
    from mud.models.object import Object


@dataclass
class ObjectInstance:
    """Runtime instance of an object."""
    name: Optional[str]
    item_type: int
    prototype: ObjIndex
    short_descr: Optional[str] = None
    location: Optional['Room'] = None
    contained_items: List['ObjectInstance'] = field(default_factory=list)

    def move_to_room(self, room: 'Room') -> None:
        if self.location and hasattr(self.location, 'contents'):
            if self in self.location.contents:
                self.location.contents.remove(self)
        room.contents.append(self)
        self.location = room


@dataclass
class MobInstance:
    """Runtime instance of a mob (NPC)."""
    name: Optional[str]
    level: int
    current_hp: int
    prototype: MobIndex
    inventory: List[Object] = field(default_factory=list)
    room: Optional['Room'] = None
    # Minimal encumbrance fields to interoperate with move_character
    carry_weight: int = 0
    carry_number: int = 0

    @classmethod
    def from_prototype(cls, proto: MobIndex) -> 'MobInstance':
        return cls(name=proto.short_descr or proto.player_name,
                   level=proto.level,
                   current_hp=proto.hit[1],
                   prototype=proto)

    def move_to_room(self, room: 'Room') -> None:
        if self.room and self in self.room.people:
            self.room.people.remove(self)
        room.people.append(self)
        self.room = room

    def add_to_inventory(self, obj: Object) -> None:
        self.inventory.append(obj)

    def equip(self, obj: Object, slot: int) -> None:  # stub
        self.add_to_inventory(obj)
