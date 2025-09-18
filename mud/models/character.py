from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING

from mud.models.constants import AffectFlag, Position, Stat

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
    position: int = Position.STANDING
    room: Optional["Room"] = None
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
    inventory: List["Object"] = field(default_factory=list)
    equipment: Dict[str, "Object"] = field(default_factory=dict)
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
    # Combat skill levels (0-100) for multi-attack mechanics
    second_attack_skill: int = 0
    third_attack_skill: int = 0
    # Charm/follow hierarchy pointer (ROM ch->master)
    master: Optional["Character"] = None
    # Combat state - currently fighting target
    fighting: Optional["Character"] = None
    # Enhanced damage skill level (0-100)
    enhanced_damage_skill: int = 0
    # Character type flag
    is_npc: bool = True  # Default to NPC, set to False for PCs

    def __repr__(self) -> str:
        return f"<Character name={self.name!r} level={self.level}>"

    def is_immortal(self) -> bool:
        """Check if character is immortal (ROM IS_IMMORTAL macro)."""
        from mud.models.constants import LEVEL_IMMORTAL

        # For NPCs, use level; for PCs, use trust (which defaults to level if not set)
        effective_level = self.trust if self.trust > 0 else self.level
        return effective_level >= LEVEL_IMMORTAL

    def is_awake(self) -> bool:
        """Return True if the character is awake (not sleeping or worse)."""

        return self.position > Position.SLEEPING

    @staticmethod
    def _stat_from_list(values: List[int], stat: int) -> Optional[int]:
        if not values:
            return None
        idx = int(stat)
        if idx < 0 or idx >= len(values):
            return None
        val = values[idx]
        if val is None:
            return None
        return int(val)

    def get_curr_stat(self, stat: int | Stat) -> Optional[int]:
        """Compute current stat (perm + mod) clamped to ROM 0..25."""

        idx = int(stat)
        base_val = self._stat_from_list(self.perm_stat, idx)
        mod_val = self._stat_from_list(self.mod_stat, idx)
        if base_val is None and mod_val is None:
            return None
        total = (base_val or 0) + (mod_val or 0)
        return max(0, min(25, total))

    def get_int_learn_rate(self) -> int:
        """Return int_app.learn value for the character's current INT."""

        stat_val = self.get_curr_stat(Stat.INT)
        if stat_val is None:
            return _DEFAULT_INT_LEARN
        idx = max(0, min(stat_val, len(_INT_LEARN_RATES) - 1))
        return _INT_LEARN_RATES[idx]

    def skill_adept_cap(self) -> int:
        """Return the maximum practiced percentage allowed for this character."""

        if self.is_npc:
            return 100
        return _CLASS_SKILL_ADEPT.get(self.ch_class, _CLASS_SKILL_ADEPT_DEFAULT)

    def send_to_char(self, message: str) -> None:
        """Append a message to the character's buffer (used in tests)."""

        self.messages.append(message)

    def add_object(self, obj: "Object") -> None:
        self.inventory.append(obj)
        self.carry_number += 1
        self.carry_weight += getattr(obj.prototype, "weight", 0)

    def equip_object(self, obj: "Object", slot: str) -> None:
        if obj in self.inventory:
            self.inventory.remove(obj)
        else:
            self.carry_number += 1
            self.carry_weight += getattr(obj.prototype, "weight", 0)
        self.equipment[slot] = obj

    def remove_object(self, obj: "Object") -> None:
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

    def strip_affect(self, affect_name: str) -> None:
        """Strip affect by name (simplified for combat system)."""
        if affect_name == "sleep":
            self.remove_affect(AffectFlag.SLEEP)
        # Add other affects as needed


# END affects_saves


character_registry: list[Character] = []


def from_orm(db_char: "DBCharacter") -> Character:
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


def to_orm(character: Character, player_id: int) -> "DBCharacter":
    from mud.db.models import Character as DBCharacter

    return DBCharacter(
        name=character.name,
        level=character.level,
        hp=character.hit,
        room_vnum=character.room.vnum if character.room else None,
        player_id=player_id,
    )
_INT_LEARN_RATES: list[int] = [
    3,
    5,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    15,
    17,
    19,
    22,
    25,
    28,
    31,
    34,
    37,
    40,
    44,
    49,
    55,
    60,
    70,
    80,
    85,
]

_DEFAULT_INT_LEARN = _INT_LEARN_RATES[13]  # INT 13 is baseline in ROM.

_CLASS_SKILL_ADEPT: dict[int, int] = {
    0: 75,  # mage
    1: 75,  # cleric
    2: 75,  # thief
    3: 75,  # warrior
}

_CLASS_SKILL_ADEPT_DEFAULT = 75

