from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.object import Object
    from mud.db.models import Character as DBCharacter

@dataclass
class PCData:
    """Subset of PC_DATA from merc.h"""
    pwd: Optional[str] = None
    bamfin: Optional[str] = None
    bamfout: Optional[str] = None
    title: Optional[str] = None
    perm_hit: int = 0
    perm_mana: int = 0
    perm_move: int = 0
    true_sex: int = 0
    last_level: int = 0
    condition: List[int] = field(default_factory=lambda: [0] * 4)
    points: int = 0
    security: int = 0

@dataclass
class Character:
    """Python representation of CHAR_DATA"""
    name: Optional[str] = None
    short_descr: Optional[str] = None
    long_descr: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    prefix: Optional[str] = None
    sex: int = 0
    ch_class: int = 0
    race: int = 0
    level: int = 0
    trust: int = 0
    hit: int = 0
    max_hit: int = 0
    mana: int = 0
    max_mana: int = 0
    move: int = 0
    max_move: int = 0
    gold: int = 0
    silver: int = 0
    exp: int = 0
    act: int = 0
    affected_by: int = 0
    position: int = 0
    practice: int = 0
    train: int = 0
    carry_weight: int = 0
    carry_number: int = 0
    saving_throw: int = 0
    alignment: int = 0
    hitroll: int = 0
    damroll: int = 0
    wimpy: int = 0
    perm_stat: List[int] = field(default_factory=list)
    mod_stat: List[int] = field(default_factory=list)
    form: int = 0
    parts: int = 0
    size: int = 0
    material: Optional[str] = None
    off_flags: int = 0
    damage: List[int] = field(default_factory=lambda: [0, 0, 0])
    dam_type: int = 0
    start_pos: int = 0
    default_pos: int = 0
    mprog_delay: int = 0
    pcdata: Optional[PCData] = None
    inventory: List['Object'] = field(default_factory=list)
    equipment: Dict[str, 'Object'] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    connection: Optional[object] = None
    is_admin: bool = False

    def __repr__(self) -> str:
        return f"<Character name={self.name!r} level={self.level}>"

    def add_object(self, obj: 'Object') -> None:
        self.inventory.append(obj)

    def equip_object(self, obj: 'Object', slot: str) -> None:
        if obj in self.inventory:
            self.inventory.remove(obj)
        self.equipment[slot] = obj


character_registry: list[Character] = []


def from_orm(db_char: 'DBCharacter') -> Character:
    from mud.registry import room_registry

    room = room_registry.get(db_char.room_vnum)
    char = Character(
        name=db_char.name,
        level=db_char.level or 0,
        hit=db_char.hp or 0,
    )
    char.room = room
    if db_char.player is not None:
        char.is_admin = bool(getattr(db_char.player, "is_admin", False))
    return char


def to_orm(character: Character, player_id: int) -> 'DBCharacter':
    from mud.db.models import Character as DBCharacter

    return DBCharacter(
        name=character.name,
        level=character.level,
        hp=character.hit,
        room_vnum=character.room.vnum if getattr(character, "room", None) else None,
        player_id=player_id,
    )
