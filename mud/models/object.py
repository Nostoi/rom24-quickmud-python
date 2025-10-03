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
    # Instance values — copy of prototype.value for runtime mutations (e.g., locks/charges)
    value: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    # ROM runtime state persisted alongside prototypes
    timer: int = 0
    wear_loc: int = int(WearLocation.NONE)
    cost: int = 0
    extra_flags: int = 0
    wear_flags: int = 0
    condition: int | str = 0
    enchanted: bool = False
    item_type: str | None = None
    affected: list[Affect] = field(default_factory=list)

    @property
    def name(self) -> str | None:
        return self.prototype.name

    @property
    def short_descr(self) -> str | None:
        return getattr(self.prototype, "short_descr", None)
