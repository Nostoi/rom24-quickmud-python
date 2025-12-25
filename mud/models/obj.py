from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .room import ExtraDescr, Room

if TYPE_CHECKING:
    from .area import Area
    from .character import Character


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


@dataclass
class ObjectData:
    """Python representation of OBJ_DATA (ROM src/merc.h struct obj_data)"""

    # Core properties
    item_type: int
    valid: bool = True  # ROM: bool valid (object validity flag)
    enchanted: bool = False  # ROM: bool enchanted (magical enhancement flag)
    
    # Flags and attributes
    extra_flags: int = 0
    wear_flags: int = 0
    wear_loc: int = 0
    weight: int = 0
    cost: int = 0
    level: int = 0
    condition: int = 0
    timer: int = 0
    value: list[int] = field(default_factory=lambda: [0] * 5)
    
    # Descriptive fields
    owner: str | None = None
    name: str | None = None
    short_descr: str | None = None
    description: str | None = None
    material: str | None = None
    
    # Relationships and containment
    carried_by: Character | None = None  # ROM: CHAR_DATA *carried_by
    in_obj: ObjectData | None = None  # ROM: OBJ_DATA *in_obj (container)
    on: Character | None = None  # ROM: OBJ_DATA *on (worn on character - we use wear_loc + carried_by)
    contains: list[ObjectData] = field(default_factory=list)  # ROM: OBJ_DATA *contains
    extra_descr: list[ExtraDescr] = field(default_factory=list)  # ROM: EXTRA_DESCR_DATA *extra_descr
    affected: list[Affect] = field(default_factory=list)  # ROM: AFFECT_DATA *affected
    
    # Index and location
    pIndexData: ObjIndex | None = None  # ROM: OBJ_INDEX_DATA *pIndexData
    in_room: Room | None = None  # ROM: ROOM_INDEX_DATA *in_room
    
    # Linked list pointers (Python uses lists but we keep for compatibility)
    next_content: ObjectData | None = None  # ROM: OBJ_DATA *next_content
    next: ObjectData | None = None  # ROM: OBJ_DATA *next

    def __repr__(self) -> str:
        return f"<ObjectData type={self.item_type} name={self.short_descr!r}>"


object_registry: list[ObjectData] = []
