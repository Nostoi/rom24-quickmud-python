from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .room import Room

from .obj import Affect, ObjIndex
from .constants import WearLocation


@dataclass
class Object:
    """Instance of an object tied to a prototype."""

    instance_id: int | None
    prototype: ObjIndex
    location: Room | None = None
    contained_items: list[Object] = field(default_factory=list)
    level: int = 0
    value: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    timer: int = 0
    wear_loc: int = int(WearLocation.NONE)
    cost: int = 0
    extra_flags: int = 0
    wear_flags: int = 0
    condition: int | str = 0
    enchanted: bool = False
    item_type: str | None = None
    owner: str | None = None
    affected: list[Affect] = field(default_factory=list)
    _short_descr_override: str | None = field(default=None, repr=False)
    _description_override: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Mirror prototype defaults onto the instance.

        ROM Reference: src/db.c:create_object — instance copies extra_flags,
        wear_flags, level, value, weight, etc. from the prototype unless the
        spawner has already supplied an override. Tests that build Object
        instances directly (without going through the spawner) rely on this
        sync so flags like ITEM_NOREMOVE / ITEM_NODROP are honored.
        """
        proto = self.prototype
        if proto is None:
            return
        if not self.extra_flags:
            proto_extra = getattr(proto, "extra_flags", 0)
            try:
                self.extra_flags = int(proto_extra) if proto_extra else 0
            except (TypeError, ValueError):
                self.extra_flags = 0
        if not self.wear_flags:
            proto_wear = getattr(proto, "wear_flags", 0)
            try:
                self.wear_flags = int(proto_wear) if proto_wear else 0
            except (TypeError, ValueError):
                self.wear_flags = 0
        if self.item_type is None:
            proto_item_type = getattr(proto, "item_type", None)
            if proto_item_type is not None:
                self.item_type = proto_item_type

    @property
    def name(self) -> str | None:
        return self.prototype.name

    @property
    def short_descr(self) -> str | None:
        if self._short_descr_override is not None:
            return self._short_descr_override
        return getattr(self.prototype, "short_descr", None)

    @short_descr.setter
    def short_descr(self, value: str | None) -> None:
        self._short_descr_override = value

    @property
    def description(self) -> str | None:
        if self._description_override is not None:
            return self._description_override
        return getattr(self.prototype, "description", None)

    @description.setter
    def description(self, value: str | None) -> None:
        self._description_override = value
