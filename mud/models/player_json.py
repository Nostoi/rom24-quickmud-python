from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .json_io import JsonDataclass


@dataclass
class PlayerJson(JsonDataclass):
    """Player record matching ``schemas/player.schema.json``."""

    name: str
    level: int
    hit: int
    max_hit: int
    mana: int
    max_mana: int
    move: int
    max_move: int
    gold: int
    silver: int
    exp: int
    position: int
    room_vnum: Optional[int]
    inventory: List[int] = field(default_factory=list)
    equipment: Dict[str, int] = field(default_factory=dict)
    plr_flags: int = 0
    comm_flags: int = 0
