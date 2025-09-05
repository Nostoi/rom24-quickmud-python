from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .room_json import ResetJson


@dataclass
class Area:
    """Runtime area container loaded from legacy files."""
    file_name: Optional[str] = None
    name: Optional[str] = None
    credits: Optional[str] = None
    age: int = 0
    nplayer: int = 0
    low_range: int = 0
    high_range: int = 0
    min_vnum: int = 0
    max_vnum: int = 0
    empty: bool = False
    builders: Optional[str] = None
    vnum: int = 0
    area_flags: int = 0
    security: int = 0
    helps: List[object] = field(default_factory=list)
    resets: List[ResetJson] = field(default_factory=list)
    next: Optional['Area'] = None

    def __repr__(self) -> str:
        return f"<Area vnum={self.vnum} name={self.name!r}>"


area_registry: dict[int, Area] = {}
