from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from mud.models.character import Character, PCData, character_registry
from mud.models.json_io import dump_dataclass, load_dataclass
from mud.notes import DEFAULT_BOARD_NAME, find_board, get_board
from mud.registry import room_registry
from mud.spawning.obj_spawner import spawn_object
from mud.time import Sunlight, time_info


def _normalize_int_list(values: Iterable[int] | None, length: int) -> list[int]:
    """Return a list of ``length`` integers padded/truncated from ``values``."""

    normalized = [0] * length
    if not values:
        return normalized
    for idx, value in enumerate(list(values)[:length]):
        try:
            normalized[idx] = int(value)
        except (TypeError, ValueError):
            normalized[idx] = 0
    return normalized


@dataclass
class PlayerSave:
    """Serializable snapshot of a player's state."""

    name: str
    level: int
    race: int = 0
    ch_class: int = 0
    sex: int = 0
    trust: int = 0
    security: int = 0
    hit: int = 0
    max_hit: int = 0
    mana: int = 0
    max_mana: int = 0
    move: int = 0
    max_move: int = 0
    perm_hit: int = 0
    perm_mana: int = 0
    perm_move: int = 0
    gold: int = 0
    silver: int = 0
    exp: int = 0
    practice: int = 0
    train: int = 0
    saving_throw: int = 0
    alignment: int = 0
    hitroll: int = 0
    damroll: int = 0
    wimpy: int = 0
    points: int = 0
    true_sex: int = 0
    last_level: int = 0
    position: int = 0
    armor: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    perm_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    mod_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    conditions: list[int] = field(default_factory=lambda: [0, 48, 48, 48])
    # ROM bitfields to preserve flags parity
    act: int = 0
    affected_by: int = 0
    comm: int = 0
    wiznet: int = 0
    log_commands: bool = False
    room_vnum: int | None = None
    inventory: list[int] = field(default_factory=list)
    equipment: dict[str, int] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    board: str = DEFAULT_BOARD_NAME
    last_notes: dict[str, float] = field(default_factory=dict)


PLAYERS_DIR = Path("data/players")
TIME_FILE = Path("data/time.json")


def save_character(char: Character) -> None:
    """Persist ``char`` to ``PLAYERS_DIR`` as JSON."""
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
    default_conditions = [0, 48, 48, 48]
    raw_conditions: list[int] = []
    pcdata = char.pcdata or PCData()
    raw_conditions = list(getattr(pcdata, "condition", []))
    conditions = default_conditions.copy()
    for idx, value in enumerate(raw_conditions[:4]):
        conditions[idx] = int(value)
    armor = _normalize_int_list(getattr(char, "armor", []), 4)
    perm_stat = _normalize_int_list(getattr(char, "perm_stat", []), 5)
    mod_stat = _normalize_int_list(getattr(char, "mod_stat", []), 5)
    data = PlayerSave(
        name=char.name or "",
        level=char.level,
        race=int(getattr(char, "race", 0)),
        ch_class=int(getattr(char, "ch_class", 0)),
        sex=int(getattr(char, "sex", 0)),
        trust=int(getattr(char, "trust", 0)),
        security=int(getattr(pcdata, "security", 0)),
        hit=char.hit,
        max_hit=char.max_hit,
        mana=char.mana,
        max_mana=char.max_mana,
        move=char.move,
        max_move=char.max_move,
        perm_hit=int(getattr(pcdata, "perm_hit", 0)),
        perm_mana=int(getattr(pcdata, "perm_mana", 0)),
        perm_move=int(getattr(pcdata, "perm_move", 0)),
        gold=char.gold,
        silver=char.silver,
        exp=char.exp,
        practice=int(getattr(char, "practice", 0)),
        train=int(getattr(char, "train", 0)),
        saving_throw=int(getattr(char, "saving_throw", 0)),
        alignment=int(getattr(char, "alignment", 0)),
        hitroll=int(getattr(char, "hitroll", 0)),
        damroll=int(getattr(char, "damroll", 0)),
        wimpy=int(getattr(char, "wimpy", 0)),
        points=int(getattr(pcdata, "points", 0)),
        true_sex=int(getattr(pcdata, "true_sex", 0)),
        last_level=int(getattr(pcdata, "last_level", 0)),
        position=char.position,
        armor=armor,
        perm_stat=perm_stat,
        mod_stat=mod_stat,
        conditions=conditions,
        act=getattr(char, "act", 0),
        affected_by=getattr(char, "affected_by", 0),
        comm=getattr(char, "comm", 0),
        wiznet=getattr(char, "wiznet", 0),
        log_commands=bool(getattr(char, "log_commands", False)),
        room_vnum=char.room.vnum if getattr(char, "room", None) else None,
        inventory=[obj.prototype.vnum for obj in char.inventory],
        equipment={slot: obj.prototype.vnum for slot, obj in char.equipment.items()},
        aliases=dict(getattr(char, "aliases", {})),
        board=getattr(pcdata, "board_name", DEFAULT_BOARD_NAME) or DEFAULT_BOARD_NAME,
        last_notes=dict(getattr(pcdata, "last_notes", {}) or {}),
    )
    path = PLAYERS_DIR / f"{char.name.lower()}.json"
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        dump_dataclass(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def load_character(name: str) -> Character | None:
    """Load a character by ``name`` from ``PLAYERS_DIR``."""
    path = PLAYERS_DIR / f"{name.lower()}.json"
    if not path.exists():
        return None
    with path.open() as f:
        data = load_dataclass(PlayerSave, f)
    armor = _normalize_int_list(getattr(data, "armor", []), 4)
    perm_stat = _normalize_int_list(getattr(data, "perm_stat", []), 5)
    mod_stat = _normalize_int_list(getattr(data, "mod_stat", []), 5)
    char = Character(
        name=data.name,
        level=data.level,
        race=int(getattr(data, "race", 0)),
        ch_class=int(getattr(data, "ch_class", 0)),
        sex=int(getattr(data, "sex", 0)),
        trust=int(getattr(data, "trust", 0)),
        hit=data.hit,
        max_hit=data.max_hit,
        mana=data.mana,
        max_mana=data.max_mana,
        move=data.move,
        max_move=data.max_move,
        gold=data.gold,
        silver=data.silver,
        exp=data.exp,
        act=int(getattr(data, "act", 0)),
        practice=int(getattr(data, "practice", 0)),
        train=int(getattr(data, "train", 0)),
        saving_throw=int(getattr(data, "saving_throw", 0)),
        alignment=int(getattr(data, "alignment", 0)),
        hitroll=int(getattr(data, "hitroll", 0)),
        damroll=int(getattr(data, "damroll", 0)),
        wimpy=int(getattr(data, "wimpy", 0)),
        comm=int(getattr(data, "comm", 0)),
        position=data.position,
        armor=armor,
        perm_stat=perm_stat,
        mod_stat=mod_stat,
    )
    char.is_npc = False
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
    board_name = getattr(data, "board", DEFAULT_BOARD_NAME) or DEFAULT_BOARD_NAME
    board = find_board(board_name)
    if board is None:
        board = find_board(DEFAULT_BOARD_NAME)
        if board is None:
            board = get_board(DEFAULT_BOARD_NAME)
    pcdata = PCData()
    saved_conditions = list(getattr(data, "conditions", []))
    conditions = [0, 48, 48, 48]
    for idx, value in enumerate(saved_conditions[:4]):
        conditions[idx] = int(value)
    pcdata.condition = conditions
    pcdata.security = int(getattr(data, "security", 0))
    pcdata.points = int(getattr(data, "points", 0))
    pcdata.true_sex = int(getattr(data, "true_sex", 0))
    pcdata.last_level = int(getattr(data, "last_level", 0))
    pcdata.perm_hit = int(getattr(data, "perm_hit", 0))
    pcdata.perm_mana = int(getattr(data, "perm_mana", 0))
    pcdata.perm_move = int(getattr(data, "perm_move", 0))
    pcdata.board_name = board.storage_key()
    pcdata.last_notes.update(getattr(data, "last_notes", {}) or {})
    char.pcdata = pcdata
    char.log_commands = bool(getattr(data, "log_commands", False))
    character_registry.append(char)
    return char


def save_world() -> None:
    """Write all registered characters to disk."""
    save_time_info()
    for char in list(character_registry):
        if char.name:
            save_character(char)


def load_world() -> list[Character]:
    """Load all character files from ``PLAYERS_DIR``."""
    chars: list[Character] = []
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
