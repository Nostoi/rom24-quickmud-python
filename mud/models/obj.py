from __future__ import annotations
from .room import ExtraDescr, Room
from .character import Character
from dataclasses import dataclass, field
from typing import List, Optional

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
    name: Optional[str] = None
    short_descr: Optional[str] = None
    description: Optional[str] = None
    material: Optional[str] = None
    item_type: str = 'trash'
    extra_flags: int = 0
    wear_flags: str = ''
    level: int = 0
    condition: str = 'P'
    count: int = 0
    weight: int = 0
    cost: int = 0
    value: List[int] = field(default_factory=lambda: [0] * 5)
    affects: List[dict] = field(default_factory=list)  # {'location': int, 'modifier': int}
    extra_descr: List[dict] = field(default_factory=list)  # {'keyword': str, 'description': str}
    area: Optional['Area'] = None
    new_format: bool = False
    reset_num: int = 0
    next: Optional['ObjIndex'] = None
    # Legacy compatibility
    affected: List[Affect] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<ObjIndex vnum={self.vnum} name={self.short_descr!r}>"

obj_index_registry: dict[int, ObjIndex] = {}

@dataclass
class ObjectData:
    """Python representation of OBJ_DATA"""
    item_type: int
    extra_flags: int = 0
    wear_flags: int = 0
    wear_loc: int = 0
    weight: int = 0
    cost: int = 0
    level: int = 0
    condition: int = 0
    timer: int = 0
    value: List[int] = field(default_factory=lambda: [0] * 5)
    owner: Optional[str] = None
    name: Optional[str] = None
    short_descr: Optional[str] = None
    description: Optional[str] = None
    material: Optional[str] = None
    carried_by: Optional['Character'] = None
    in_obj: Optional['ObjectData'] = None
    contains: List['ObjectData'] = field(default_factory=list)
    extra_descr: List['ExtraDescr'] = field(default_factory=list)
    affected: List[Affect] = field(default_factory=list)
    pIndexData: Optional[ObjIndex] = None
    in_room: Optional['Room'] = None
    enchanted: bool = False
    next_content: Optional['ObjectData'] = None
    next: Optional['ObjectData'] = None

    def __repr__(self) -> str:
        return f"<ObjectData type={self.item_type} name={self.short_descr!r}>"


object_registry: list[ObjectData] = []
