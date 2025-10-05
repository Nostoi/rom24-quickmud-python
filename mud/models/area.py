from __future__ import annotations

from dataclasses import dataclass, field

from .room_json import ResetJson


@dataclass
class Area:
    """Runtime area container loaded from legacy files."""

    file_name: str | None = None
    name: str | None = None
    credits: str | None = None
    age: int = 0
    nplayer: int = 0
    low_range: int = 0
    high_range: int = 0
    min_vnum: int = 0
    max_vnum: int = 0
    empty: bool = False
    builders: str | None = None
    vnum: int = 0
    area_flags: int = 0
    security: int = 0
    helps: list[object] = field(default_factory=list)
    resets: list[ResetJson] = field(default_factory=list)
    next: Area | None = None
    changed: bool = False

    def __repr__(self) -> str:
        return f"<Area vnum={self.vnum} name={self.name!r}>"


area_registry: dict[int, Area] = {}
