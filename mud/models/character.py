from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING

from mud.models.constants import AffectFlag

if TYPE_CHECKING:
    from mud.models.object import Object
    from mud.models.room import Room
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
    room: Optional['Room'] = None
    practice: int = 0
    train: int = 0
    skills: Dict[str, int] = field(default_factory=dict)
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
    # ROM parity: immunity/resistance/vulnerability bitvectors (merc.h)
    imm_flags: int = 0
    res_flags: int = 0
    vuln_flags: int = 0
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
    muted_channels: set[str] = field(default_factory=set)
    banned_channels: set[str] = field(default_factory=set)
    wiznet: int = 0
    # Wait-state (pulses) applied by actions like movement (ROM WAIT_STATE)
    wait: int = 0
    # Daze (pulses) — separate action delay used by ROM combat
    daze: int = 0
    # Armor class per index [AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC]
    armor: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    # Per-character command aliases: name -> expansion (pre-dispatch)
    aliases: Dict[str, str] = field(default_factory=dict)
    # Optional defense chances (percent) for parity-friendly tests
    shield_block_chance: int = 0
    parry_chance: int = 0
    dodge_chance: int = 0

    def __repr__(self) -> str:
        return f"<Character name={self.name!r} level={self.level}>"

    def add_object(self, obj: 'Object') -> None:
        self.inventory.append(obj)
        self.carry_number += 1
        self.carry_weight += getattr(obj.prototype, "weight", 0)

    def equip_object(self, obj: 'Object', slot: str) -> None:
        if obj in self.inventory:
            self.inventory.remove(obj)
        else:
            self.carry_number += 1
            self.carry_weight += getattr(obj.prototype, "weight", 0)
        self.equipment[slot] = obj

    def remove_object(self, obj: 'Object') -> None:
        if obj in self.inventory:
            self.inventory.remove(obj)
        else:
            for slot, eq in list(self.equipment.items()):
                if eq is obj:
                    del self.equipment[slot]
                    break
        self.carry_number -= 1
        self.carry_weight -= getattr(obj.prototype, "weight", 0)

# START affects_saves
    def add_affect(
        self,
        flag: AffectFlag,
        *,
        hitroll: int = 0,
        damroll: int = 0,
        saving_throw: int = 0,
    ) -> None:
        """Apply an affect flag and modify core stats."""
        self.affected_by |= flag
        self.hitroll += hitroll
        self.damroll += damroll
        self.saving_throw += saving_throw

    def has_affect(self, flag: AffectFlag) -> bool:
        return bool(self.affected_by & flag)

    def remove_affect(
        self,
        flag: AffectFlag,
        *,
        hitroll: int = 0,
        damroll: int = 0,
        saving_throw: int = 0,
    ) -> None:
        """Remove an affect flag and revert stat modifications."""
        self.affected_by &= ~flag
        self.hitroll -= hitroll
        self.damroll -= damroll
        self.saving_throw -= saving_throw
# END affects_saves


character_registry: list[Character] = []


def from_orm(db_char: 'DBCharacter') -> Character:
    from mud.registry import room_registry
    from mud.models.constants import Position

    room = room_registry.get(db_char.room_vnum)
    char = Character(
        name=db_char.name,
        level=db_char.level or 0,
        hit=db_char.hp or 0,
        position=int(Position.STANDING),  # Default to standing for loaded chars
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
        room_vnum=character.room.vnum if character.room else None,
        player_id=player_id,
    )
