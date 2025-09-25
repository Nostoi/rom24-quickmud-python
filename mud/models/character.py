from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag, Position, Stat

if TYPE_CHECKING:
    from mud.db.models import Character as DBCharacter
    from mud.models.board import NoteDraft
    from mud.models.mob import MobProgram
    from mud.models.object import Object
    from mud.models.room import Room


@dataclass
class PCData:
    """Subset of PC_DATA from merc.h"""

    pwd: str | None = None
    bamfin: str | None = None
    bamfout: str | None = None
    title: str | None = None
    perm_hit: int = 0
    perm_mana: int = 0
    perm_move: int = 0
    true_sex: int = 0
    last_level: int = 0
    condition: list[int] = field(default_factory=lambda: [0] * 4)
    points: int = 0
    security: int = 0
    board_name: str = "general"
    last_notes: dict[str, float] = field(default_factory=dict)
    in_progress: NoteDraft | None = None


@dataclass
class SpellEffect:
    """Lightweight spell affect tracker mirroring ROM's AFFECT_DATA."""

    name: str
    duration: int
    ac_mod: int = 0
    hitroll_mod: int = 0
    damroll_mod: int = 0
    saving_throw_mod: int = 0
    affect_flag: AffectFlag | None = None


@dataclass
class Character:
    """Python representation of CHAR_DATA"""

    name: str | None = None
    short_descr: str | None = None
    long_descr: str | None = None
    description: str | None = None
    prompt: str | None = None
    prefix: str | None = None
    sex: int = 0
    ch_class: int = 0
    race: int = 0
    level: int = 0
    trust: int = 0
    invis_level: int = 0
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
    room: Room | None = None
    master: Character | None = None
    leader: Character | None = None
    practice: int = 0
    train: int = 0
    skills: dict[str, int] = field(default_factory=dict)
    carry_weight: int = 0
    carry_number: int = 0
    saving_throw: int = 0
    alignment: int = 0
    hitroll: int = 0
    damroll: int = 0
    wimpy: int = 0
    perm_stat: list[int] = field(default_factory=list)
    mod_stat: list[int] = field(default_factory=list)
    form: int = 0
    parts: int = 0
    size: int = 0
    material: str | None = None
    off_flags: int = 0
    # ROM parity: immunity/resistance/vulnerability bitvectors (merc.h)
    imm_flags: int = 0
    res_flags: int = 0
    vuln_flags: int = 0
    damage: list[int] = field(default_factory=lambda: [0, 0, 0])
    dam_type: int = 0
    start_pos: int = 0
    default_pos: int = 0
    mprog_delay: int = 0
    pcdata: PCData | None = None
    inventory: list[Object] = field(default_factory=list)
    equipment: dict[str, Object] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    connection: object | None = None
    is_admin: bool = False
    muted_channels: set[str] = field(default_factory=set)
    banned_channels: set[str] = field(default_factory=set)
    wiznet: int = 0
    # Wait-state (pulses) applied by actions like movement (ROM WAIT_STATE)
    wait: int = 0
    # Daze (pulses) — separate action delay used by ROM combat
    daze: int = 0
    # Armor class per index [AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC]
    armor: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    # Per-character command aliases: name -> expansion (pre-dispatch)
    aliases: dict[str, str] = field(default_factory=dict)
    # Optional defense chances (percent) for parity-friendly tests
    shield_block_chance: int = 0
    parry_chance: int = 0
    dodge_chance: int = 0
    # Combat skill levels (0-100) for multi-attack mechanics
    second_attack_skill: int = 0
    third_attack_skill: int = 0
    # Combat state - currently fighting target
    fighting: Character | None = None
    # Enhanced damage skill level (0-100)
    enhanced_damage_skill: int = 0
    # Character type flag
    is_npc: bool = True  # Default to NPC, set to False for PCs
    # Mob program runtime state mirroring ROM's CHAR_DATA fields
    mob_programs: list[MobProgram] = field(default_factory=list)
    mprog_target: Character | None = None
    # Active spell effects keyed by skill name for parity restores
    spell_effects: dict[str, SpellEffect] = field(default_factory=dict)

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
    def _stat_from_list(values: list[int], stat: int) -> int | None:
        if not values:
            return None
        idx = int(stat)
        if idx < 0 or idx >= len(values):
            return None
        val = values[idx]
        if val is None:
            return None
        return int(val)

    def get_curr_stat(self, stat: int | Stat) -> int | None:
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

    def add_object(self, obj: Object) -> None:
        self.inventory.append(obj)
        self.carry_number += 1
        self.carry_weight += getattr(obj.prototype, "weight", 0)

    def equip_object(self, obj: Object, slot: str) -> None:
        if obj in self.inventory:
            self.inventory.remove(obj)
        else:
            self.carry_number += 1
            self.carry_weight += getattr(obj.prototype, "weight", 0)
        self.equipment[slot] = obj

    def remove_object(self, obj: Object) -> None:
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

    def has_spell_effect(self, name: str) -> bool:
        """Check if a named spell affect is active (ROM is_affected equivalent)."""
        return name in self.spell_effects

    def apply_spell_effect(self, effect: SpellEffect) -> bool:
        """Apply a spell effect while preventing duplicate stacking."""
        if self.has_spell_effect(effect.name):
            return False

        if effect.ac_mod:
            self.armor = [ac + effect.ac_mod for ac in self.armor]
        if effect.hitroll_mod:
            self.hitroll += effect.hitroll_mod
        if effect.damroll_mod:
            self.damroll += effect.damroll_mod
        if effect.saving_throw_mod:
            self.saving_throw += effect.saving_throw_mod
        if effect.affect_flag is not None:
            self.add_affect(effect.affect_flag)

        self.spell_effects[effect.name] = effect
        return True

    def remove_spell_effect(self, name: str) -> None:
        """Remove a spell effect and restore stat changes."""
        effect = self.spell_effects.pop(name, None)
        if effect is None:
            return

        if effect.ac_mod:
            self.armor = [ac - effect.ac_mod for ac in self.armor]
        if effect.hitroll_mod:
            self.hitroll -= effect.hitroll_mod
        if effect.damroll_mod:
            self.damroll -= effect.damroll_mod
        if effect.saving_throw_mod:
            self.saving_throw -= effect.saving_throw_mod
        if effect.affect_flag is not None:
            self.remove_affect(effect.affect_flag)


# END affects_saves


character_registry: list[Character] = []


def from_orm(db_char: DBCharacter) -> Character:
    from mud.models.constants import Position
    from mud.registry import room_registry

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


def to_orm(character: Character, player_id: int) -> DBCharacter:
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
