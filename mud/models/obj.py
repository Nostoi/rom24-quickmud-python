from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .area import Area


@dataclass
class Affect:
    """Representation of AFFECT_DATA"""

    where: int
    type: int
    level: int
    duration: int
    location: int
    modifier: int
    bitvector: int


@dataclass
class ObjIndex:
    """Python representation of OBJ_INDEX_DATA"""

    vnum: int
    name: str | None = None
    short_descr: str | None = None
    description: str | None = None
    material: str | None = None
    item_type: str | int = "trash"
    extra_flags: int | str = 0
    wear_flags: str | int = ""
    level: int = 0
    condition: str = "P"
    count: int = 0
    weight: int = 0
    cost: int = 0
    value: list[int] = field(default_factory=lambda: [0] * 5)
    affects: list[dict] = field(default_factory=list)  # {'location': int, 'modifier': int}
    extra_descr: list[dict] = field(default_factory=list)  # {'keyword': str, 'description': str}
    area: Area | None = None
    new_format: bool = False
    reset_num: int = 0
    next: ObjIndex | None = None
    # Legacy compatibility
    affected: list[Affect] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<ObjIndex vnum={self.vnum} name={self.short_descr!r}>"


obj_index_registry: dict[int, ObjIndex] = {}


# INV-012: ObjectData was deleted in 2.9.0. The dual-class runtime
# (`Object` in mud/models/object.py vs `ObjectData` here) collapsed into
# a single canonical `Object` class, which lifts the ROM-faithful field
# names (`pIndexData`, `in_room`, `in_obj`, `carried_by`, `contains`) as
# either dataclass fields or @property aliases. See
# docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-012.


# INV-012: canonical instance list (parallels ROM `object_list` in src/db.c).
# Populated by mud.spawning.obj_spawner.spawn_object and drained by
# mud.game_loop._extract_obj. The forward-string reference avoids a circular
# import (mud.models.object imports Affect, ObjIndex from this file).
object_registry: list[Object] = []  # noqa: F821 — Object lives in mud.models.object
