from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .constants import Direction

@dataclass
class ExtraDescr:
    """Python representation of EXTRA_DESCR_DATA"""
    keyword: Optional[str] = None
    description: Optional[str] = None

@dataclass
class Exit:
    """Representation of EXIT_DATA"""
    to_room: Optional['Room'] = None
    vnum: Optional[int] = None
    exit_info: int = 0
    key: int = 0
    keyword: Optional[str] = None
    description: Optional[str] = None
    rs_flags: int = 0
    orig_door: int = 0

@dataclass
class Reset:
    """Representation of RESET_DATA"""
    command: str
    arg1: int
    arg2: int
    arg3: int
    arg4: int

@dataclass
class Room:
    """Python representation of ROOM_INDEX_DATA"""
    vnum: int
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    area: Optional['Area'] = None
    room_flags: int = 0
    light: int = 0
    sector_type: int = 0
    heal_rate: int = 0
    mana_rate: int = 0
    clan: int = 0
    exits: List[Optional[Exit]] = field(default_factory=lambda: [None] * len(Direction))
    extra_descr: List[ExtraDescr] = field(default_factory=list)
    resets: List[Reset] = field(default_factory=list)
    people: List['Character'] = field(default_factory=list)
    contents: List['ObjectData'] = field(default_factory=list)
    next: Optional['Room'] = None
