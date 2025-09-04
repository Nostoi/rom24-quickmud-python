from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExitJson:
    """Exit specification for JSON rooms."""
    to_room: int
    description: Optional[str] = None
    keyword: Optional[str] = None
    flags: List[str] = field(default_factory=list)


@dataclass
class ExtraDescriptionJson:
    """Extra description block for JSON rooms."""
    keyword: str
    description: str


@dataclass
class ResetJson:
    """Reset command affecting a room."""
    command: str
    arg1: Optional[int] = None
    arg2: Optional[int] = None
    arg3: Optional[int] = None
    arg4: Optional[int] = None


@dataclass
class RoomJson:
    """Room record matching ``schemas/room.schema.json``."""
    id: int
    name: str
    description: str
    sector_type: str
    area: int
    flags: List[str] = field(default_factory=list)
    exits: Dict[str, ExitJson] = field(default_factory=dict)
    extra_descriptions: List[ExtraDescriptionJson] = field(default_factory=list)
    resets: List[ResetJson] = field(default_factory=list)
