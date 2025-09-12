from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .room import Room

from .obj import ObjIndex


@dataclass
class Object:
    """Instance of an object tied to a prototype."""
    instance_id: Optional[int]
    prototype: ObjIndex
    location: Optional['Room'] = None
    contained_items: List['Object'] = field(default_factory=list)
    level: int = 0
    # Instance values — copy of prototype.value for runtime mutations (e.g., locks/charges)
    value: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])

    @property
    def name(self) -> Optional[str]:
        return self.prototype.name

    @property
    def short_descr(self) -> Optional[str]:
        return getattr(self.prototype, "short_descr", None)
