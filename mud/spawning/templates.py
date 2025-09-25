from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mud.models.object import Object

if TYPE_CHECKING:
    from mud.models.mob import MobIndex
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.models.room import Room

from mud.models.constants import ActFlag, Position
from mud.utils import rng_mm


@dataclass
class ObjectInstance:
    """Runtime instance of an object."""

    name: str | None
    item_type: int
    prototype: ObjIndex
    short_descr: str | None = None
    location: Room | None = None
    contained_items: list[ObjectInstance] = field(default_factory=list)

    def move_to_room(self, room: Room) -> None:
        if self.location and hasattr(self.location, "contents"):
            if self in self.location.contents:
                self.location.contents.remove(self)
        room.contents.append(self)
        self.location = room


@dataclass
class MobInstance:
    """Runtime instance of a mob (NPC)."""

    name: str | None
    level: int
    current_hp: int
    prototype: MobIndex
    inventory: list[Object] = field(default_factory=list)
    room: Room | None = None
    # Minimal encumbrance fields to interoperate with move_character
    carry_weight: int = 0
    carry_number: int = 0
    position: int = Position.STANDING
    gold: int = 0
    silver: int = 0

    @classmethod
    def from_prototype(cls, proto: MobIndex) -> MobInstance:
        wealth = getattr(proto, "wealth", 0) or 0
        gold_coins = 0
        silver_coins = 0
        if wealth > 0:
            low = wealth // 2
            high = (3 * wealth) // 2
            if high < low:
                high = low
            total = rng_mm.number_range(low, high)
            gold_min = total // 200
            gold_max = max(total // 100, gold_min)
            if gold_max < gold_min:
                gold_max = gold_min
            gold_coins = rng_mm.number_range(gold_min, gold_max)
            silver_coins = max(total - gold_coins * 100, 0)
        return cls(
            name=proto.short_descr or proto.player_name,
            level=proto.level,
            current_hp=proto.hit[1],
            prototype=proto,
            gold=gold_coins,
            silver=silver_coins,
        )

    def move_to_room(self, room: Room) -> None:
        if self.room and self in self.room.people:
            self.room.people.remove(self)
        room.people.append(self)
        self.room = room

    def add_to_inventory(self, obj: Object) -> None:
        self.inventory.append(obj)

    def equip(self, obj: Object, slot: int) -> None:  # stub
        self.add_to_inventory(obj)

    def has_act_flag(self, flag: ActFlag) -> bool:
        proto = getattr(self, "prototype", None)
        if proto is None:
            return False
        checker = getattr(proto, "has_act_flag", None)
        if callable(checker):
            return bool(checker(flag))
        return False

    def has_affect(self, flag) -> bool:
        try:
            bit = int(flag)
        except Exception:
            return False
        return bool(getattr(self, "affected_by", 0) & bit)

    def is_immortal(self) -> bool:
        return False
