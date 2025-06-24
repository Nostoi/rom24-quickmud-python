from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.mob import MobIndex
    from mud.models.obj import ObjIndex


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
    inventory: List[ObjectInstance] = field(default_factory=list)
    room: Optional['Room'] = None

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

    def add_to_inventory(self, obj: ObjectInstance) -> None:
        self.inventory.append(obj)
        obj.location = None

    def equip(self, obj: ObjectInstance, slot: int) -> None:  # stub
        self.add_to_inventory(obj)
