from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os

from mud.models.character import Character, character_registry
from mud.models.json_io import dump_dataclass, load_dataclass
from mud.spawning.obj_spawner import spawn_object
from mud.registry import room_registry
from mud.time import time_info, Sunlight


@dataclass
class PlayerSave:
    """Serializable snapshot of a player's state."""

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
    # ROM bitfields to preserve flags parity
    affected_by: int = 0
    wiznet: int = 0
    room_vnum: Optional[int] = None
    inventory: List[int] = field(default_factory=list)
    equipment: Dict[str, int] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)


PLAYERS_DIR = Path("data/players")
TIME_FILE = Path("data/time.json")


def save_character(char: Character) -> None:
    """Persist ``char`` to ``PLAYERS_DIR`` as JSON."""
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
    data = PlayerSave(
        name=char.name or "",
        level=char.level,
        hit=char.hit,
        max_hit=char.max_hit,
        mana=char.mana,
        max_mana=char.max_mana,
        move=char.move,
        max_move=char.max_move,
        gold=char.gold,
        silver=char.silver,
        exp=char.exp,
        position=char.position,
        affected_by=getattr(char, "affected_by", 0),
        wiznet=getattr(char, "wiznet", 0),
        room_vnum=char.room.vnum if getattr(char, "room", None) else None,
        inventory=[obj.prototype.vnum for obj in char.inventory],
        equipment={slot: obj.prototype.vnum for slot, obj in char.equipment.items()},
        aliases=dict(getattr(char, "aliases", {})),
    )
    path = PLAYERS_DIR / f"{char.name.lower()}.json"
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        dump_dataclass(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def load_character(name: str) -> Optional[Character]:
    """Load a character by ``name`` from ``PLAYERS_DIR``."""
    path = PLAYERS_DIR / f"{name.lower()}.json"
    if not path.exists():
        return None
    with path.open() as f:
        data = load_dataclass(PlayerSave, f)
    char = Character(
        name=data.name,
        level=data.level,
        hit=data.hit,
        max_hit=data.max_hit,
        mana=data.mana,
        max_mana=data.max_mana,
        move=data.move,
        max_move=data.max_move,
        gold=data.gold,
        silver=data.silver,
        exp=data.exp,
        position=data.position,
    )
    # restore bitfields
    char.affected_by = getattr(data, "affected_by", 0)
    char.wiznet = getattr(data, "wiznet", 0)
    if data.room_vnum is not None:
        room = room_registry.get(data.room_vnum)
        if room:
            room.add_character(char)
    for vnum in data.inventory:
        obj = spawn_object(vnum)
        if obj:
            char.add_object(obj)
    for slot, vnum in data.equipment.items():
        obj = spawn_object(vnum)
        if obj:
            char.equip_object(obj, slot)
    # restore aliases
    try:
        char.aliases.update(getattr(data, "aliases", {}) or {})
    except Exception:
        pass
    character_registry.append(char)
    return char


def save_world() -> None:
    """Write all registered characters to disk."""
    save_time_info()
    for char in list(character_registry):
        if char.name:
            save_character(char)


def load_world() -> List[Character]:
    """Load all character files from ``PLAYERS_DIR``."""
    chars: List[Character] = []
    load_time_info()
    if not PLAYERS_DIR.exists():
        return chars
    for path in PLAYERS_DIR.glob("*.json"):
        char = load_character(path.stem)
        if char:
            chars.append(char)
    return chars


# --- Time persistence ---

@dataclass
class TimeSave:
    hour: int
    day: int
    month: int
    year: int
    sunlight: int


def save_time_info() -> None:
    """Persist global time_info to TIME_FILE (atomic write)."""
    TIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = TimeSave(
        hour=time_info.hour,
        day=time_info.day,
        month=time_info.month,
        year=time_info.year,
        sunlight=int(time_info.sunlight),
    )
    tmp_path = TIME_FILE.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        dump_dataclass(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, TIME_FILE)


def load_time_info() -> None:
    """Load global time_info from TIME_FILE if present."""
    if not TIME_FILE.exists():
        return
    with TIME_FILE.open() as f:
        data = load_dataclass(TimeSave, f)
    time_info.hour = data.hour
    time_info.day = data.day
    time_info.month = data.month
    time_info.year = data.year
    try:
        time_info.sunlight = Sunlight(data.sunlight)
    except Exception:
        # Fallback if invalid value
        time_info.sunlight = Sunlight.DARK
