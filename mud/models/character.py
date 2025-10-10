from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from mud.math.c_compat import c_div
from mud.models.constants import AffectFlag, CommFlag, PlayerFlag, Position, Stat

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
    learned: dict[str, int] = field(default_factory=dict)
    group_known: tuple[str, ...] = field(default_factory=tuple)
    text: list[int] = field(default_factory=lambda: _default_colour_triplet("text"))
    auction: list[int] = field(default_factory=lambda: _default_colour_triplet("auction"))
    auction_text: list[int] = field(default_factory=lambda: _default_colour_triplet("auction_text"))
    gossip: list[int] = field(default_factory=lambda: _default_colour_triplet("gossip"))
    gossip_text: list[int] = field(default_factory=lambda: _default_colour_triplet("gossip_text"))
    music: list[int] = field(default_factory=lambda: _default_colour_triplet("music"))
    music_text: list[int] = field(default_factory=lambda: _default_colour_triplet("music_text"))
    question: list[int] = field(default_factory=lambda: _default_colour_triplet("question"))
    question_text: list[int] = field(default_factory=lambda: _default_colour_triplet("question_text"))
    answer: list[int] = field(default_factory=lambda: _default_colour_triplet("answer"))
    answer_text: list[int] = field(default_factory=lambda: _default_colour_triplet("answer_text"))
    quote: list[int] = field(default_factory=lambda: _default_colour_triplet("quote"))
    quote_text: list[int] = field(default_factory=lambda: _default_colour_triplet("quote_text"))
    immtalk_text: list[int] = field(default_factory=lambda: _default_colour_triplet("immtalk_text"))
    immtalk_type: list[int] = field(default_factory=lambda: _default_colour_triplet("immtalk_type"))
    info: list[int] = field(default_factory=lambda: _default_colour_triplet("info"))
    tell: list[int] = field(default_factory=lambda: _default_colour_triplet("tell"))
    tell_text: list[int] = field(default_factory=lambda: _default_colour_triplet("tell_text"))
    reply: list[int] = field(default_factory=lambda: _default_colour_triplet("reply"))
    reply_text: list[int] = field(default_factory=lambda: _default_colour_triplet("reply_text"))
    gtell_text: list[int] = field(default_factory=lambda: _default_colour_triplet("gtell_text"))
    gtell_type: list[int] = field(default_factory=lambda: _default_colour_triplet("gtell_type"))
    say: list[int] = field(default_factory=lambda: _default_colour_triplet("say"))
    say_text: list[int] = field(default_factory=lambda: _default_colour_triplet("say_text"))
    wiznet: list[int] = field(default_factory=lambda: _default_colour_triplet("wiznet"))
    room_title: list[int] = field(default_factory=lambda: _default_colour_triplet("room_title"))
    room_text: list[int] = field(default_factory=lambda: _default_colour_triplet("room_text"))
    room_exits: list[int] = field(default_factory=lambda: _default_colour_triplet("room_exits"))
    room_things: list[int] = field(default_factory=lambda: _default_colour_triplet("room_things"))
    prompt: list[int] = field(default_factory=lambda: _default_colour_triplet("prompt"))
    fight_death: list[int] = field(default_factory=lambda: _default_colour_triplet("fight_death"))
    fight_yhit: list[int] = field(default_factory=lambda: _default_colour_triplet("fight_yhit"))
    fight_ohit: list[int] = field(default_factory=lambda: _default_colour_triplet("fight_ohit"))
    fight_thit: list[int] = field(default_factory=lambda: _default_colour_triplet("fight_thit"))
    fight_skill: list[int] = field(default_factory=lambda: _default_colour_triplet("fight_skill"))


@dataclass
class SpellEffect:
    """Lightweight spell affect tracker mirroring ROM's AFFECT_DATA."""

    name: str
    duration: int
    level: int = 0
    ac_mod: int = 0
    hitroll_mod: int = 0
    damroll_mod: int = 0
    saving_throw_mod: int = 0
    affect_flag: AffectFlag | None = None
    wear_off_message: str | None = None
    stat_modifiers: dict[Stat, int] = field(default_factory=dict)


@dataclass
class Character:
    """Python representation of CHAR_DATA"""

    name: str | None = None
    account_name: str = ""
    short_descr: str | None = None
    long_descr: str | None = None
    description: str | None = None
    prompt: str | None = None
    prefix: str | None = None
    sex: int = 0
    ch_class: int = 0
    race: int = 0
    clan: int = 0
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
    pet: "Character | None" = None
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
    lines: int = 0
    played: int = 0
    logon: int = 0
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
    hometown_vnum: int = 0
    pcdata: PCData | None = None
    inventory: list[Object] = field(default_factory=list)
    equipment: dict[str, Object] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)
    connection: object | None = None
    desc: object | None = None
    reply: Character | None = None
    is_admin: bool = False
    # IMC permission level (Notset/None/Mort/Imm/Admin/Imp)
    imc_permission: str = "Mort"
    muted_channels: set[str] = field(default_factory=set)
    banned_channels: set[str] = field(default_factory=set)
    wiznet: int = 0
    comm: int = 0
    # Per-character admin logging flag mirroring ROM PLR_LOG
    log_commands: bool = False
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
    timer: int = 0
    was_in_room: Room | None = None
    # Enhanced damage skill level (0-100)
    enhanced_damage_skill: int = 0
    # Character type flag
    is_npc: bool = True  # Default to NPC, set to False for PCs
    # Mob program runtime state mirroring ROM's CHAR_DATA fields
    mob_programs: list[MobProgram] = field(default_factory=list)
    mprog_target: Character | None = None
    # Active spell effects keyed by skill name for parity restores
    spell_effects: dict[str, SpellEffect] = field(default_factory=dict)
    default_weapon_vnum: int = 0
    creation_points: int = 0
    creation_groups: tuple[str, ...] = field(default_factory=tuple)
    ansi_enabled: bool = True

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

    def _comm_value(self) -> int:
        try:
            return int(self.comm or 0)
        except Exception:
            return 0

    def has_comm_flag(self, flag: CommFlag) -> bool:
        """Return True when the character has the provided COMM bit set."""

        return bool(self._comm_value() & int(flag))

    def set_comm_flag(self, flag: CommFlag) -> None:
        """Set the provided COMM bit."""

        self.comm = self._comm_value() | int(flag)

    def clear_comm_flag(self, flag: CommFlag) -> None:
        """Clear the provided COMM bit."""

        self.comm = self._comm_value() & ~int(flag)

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
    def _ensure_mod_stat_capacity(self) -> None:
        """Ensure mod_stat can store modifiers for all primary stats."""

        required = len(list(Stat))
        if not isinstance(self.mod_stat, list):
            self.mod_stat = list(self.mod_stat or [])
        current_len = len(self.mod_stat)
        if current_len < required:
            self.mod_stat.extend([0] * (required - current_len))

    def _apply_stat_modifier(self, stat: Stat | int, delta: int) -> None:
        """Apply a modifier to the character's temporary stat list."""

        try:
            idx = int(stat)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            return
        if delta == 0:
            return
        self._ensure_mod_stat_capacity()
        if idx < 0 or idx >= len(self.mod_stat):
            return
        current_val = self.mod_stat[idx]
        try:
            current = int(current_val or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            current = 0
        self.mod_stat[idx] = current + delta

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
        """Apply or merge a spell effect following ROM ``affect_join`` semantics."""

        existing = self.spell_effects.get(effect.name)
        combined = replace(effect)
        combined.stat_modifiers = dict(combined.stat_modifiers or {})

        if existing is not None:
            combined.level = c_div(combined.level + existing.level, 2)
            combined.duration += existing.duration
            combined.ac_mod += existing.ac_mod
            combined.hitroll_mod += existing.hitroll_mod
            combined.damroll_mod += existing.damroll_mod
            combined.saving_throw_mod += existing.saving_throw_mod
            if combined.affect_flag is None:
                combined.affect_flag = existing.affect_flag
            if not combined.wear_off_message:
                combined.wear_off_message = existing.wear_off_message
            for stat, delta in getattr(existing, "stat_modifiers", {}).items():
                combined.stat_modifiers[stat] = combined.stat_modifiers.get(stat, 0) + int(delta)
            self.remove_spell_effect(effect.name)

        if combined.ac_mod:
            self.armor = [ac + combined.ac_mod for ac in self.armor]
        if combined.hitroll_mod:
            self.hitroll += combined.hitroll_mod
        if combined.damroll_mod:
            self.damroll += combined.damroll_mod
        if combined.saving_throw_mod:
            self.saving_throw += combined.saving_throw_mod
        if combined.affect_flag is not None:
            self.add_affect(combined.affect_flag)
        for stat, delta in combined.stat_modifiers.items():
            self._apply_stat_modifier(stat, int(delta))

        self.spell_effects[combined.name] = combined
        return True

    def remove_spell_effect(self, name: str) -> SpellEffect | None:
        """Remove a spell effect and restore stat changes."""
        effect = self.spell_effects.pop(name, None)
        if effect is None:
            return None

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
        stat_mods = getattr(effect, "stat_modifiers", None)
        if isinstance(stat_mods, dict):
            for stat, delta in stat_mods.items():
                self._apply_stat_modifier(stat, -int(delta))

        return effect


# END affects_saves


character_registry: list[Character] = []


def _decode_perm_stats(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        raw = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        parts = [part for part in value.split(",") if part]
        decoded: list[int] = []
        for part in parts:
            try:
                decoded.append(int(part))
            except ValueError:
                continue
        return decoded
    if isinstance(raw, list):
        decoded = []
        for entry in raw:
            try:
                decoded.append(int(entry))
            except (TypeError, ValueError):
                continue
        return decoded
    return []


def _encode_perm_stats(values: Iterable[int]) -> str:
    return json.dumps([int(val) for val in values])


def _decode_creation_groups(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        raw = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        parts = [part.strip().lower() for part in value.split(",") if part.strip()]
        return tuple(dict.fromkeys(parts))
    if isinstance(raw, list):
        ordered: list[str] = []
        seen: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            lowered = entry.strip().lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            ordered.append(lowered)
        return tuple(ordered)
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        return (lowered,) if lowered else ()
    return ()


def _encode_creation_groups(groups: Iterable[str]) -> str:
    ordered: list[str] = []
    seen: set[str] = set()
    for name in groups:
        lowered = str(name).strip().lower()
        if not lowered or lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(lowered)
    return json.dumps(ordered)


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
    char.ch_class = db_char.ch_class or 0
    char.race = db_char.race or 0
    char.sex = db_char.sex or 0
    char.alignment = db_char.alignment or 0
    char.act = db_char.act or 0
    char.ansi_enabled = bool(char.act & int(PlayerFlag.COLOUR))
    char.practice = db_char.practice or 0
    char.train = db_char.train or 0
    char.size = db_char.size or 0
    char.form = db_char.form or 0
    char.parts = db_char.parts or 0
    char.imm_flags = db_char.imm_flags or 0
    char.res_flags = db_char.res_flags or 0
    char.vuln_flags = db_char.vuln_flags or 0
    char.hometown_vnum = db_char.hometown_vnum or 0
    char.default_weapon_vnum = db_char.default_weapon_vnum or 0
    char.creation_points = getattr(db_char, "creation_points", 0) or 0
    char.creation_groups = _decode_creation_groups(getattr(db_char, "creation_groups", ""))
    char.perm_stat = _decode_perm_stats(db_char.perm_stats)
    char.is_npc = False
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
        race=int(character.race or 0),
        ch_class=int(character.ch_class or 0),
        sex=int(character.sex or 0),
        alignment=int(character.alignment or 0),
        hometown_vnum=int(character.hometown_vnum or 0),
        perm_stats=_encode_perm_stats(character.perm_stat),
        size=int(character.size or 0),
        form=int(character.form or 0),
        parts=int(character.parts or 0),
        imm_flags=int(character.imm_flags or 0),
        res_flags=int(character.res_flags or 0),
        vuln_flags=int(character.vuln_flags or 0),
        practice=int(character.practice or 0),
        train=int(character.train or 0),
        act=int(character.act or 0),
        default_weapon_vnum=int(character.default_weapon_vnum or 0),
        creation_points=int(getattr(character, "creation_points", 0) or 0),
        creation_groups=_encode_creation_groups(getattr(character, "creation_groups", ())),
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
_COLOUR_NORMAL = 0
_COLOUR_BRIGHT = 1
_COLOUR_BLACK = 0
_COLOUR_RED = 1
_COLOUR_GREEN = 2
_COLOUR_YELLOW = 3
_COLOUR_BLUE = 4
_COLOUR_MAGENTA = 5
_COLOUR_CYAN = 6
_COLOUR_WHITE = 7

_DEFAULT_PC_COLOUR_TABLE: dict[str, tuple[int, int, int]] = {
    "text": (_COLOUR_NORMAL, _COLOUR_WHITE, 0),
    "auction": (_COLOUR_BRIGHT, _COLOUR_YELLOW, 0),
    "auction_text": (_COLOUR_BRIGHT, _COLOUR_WHITE, 0),
    "gossip": (_COLOUR_NORMAL, _COLOUR_MAGENTA, 0),
    "gossip_text": (_COLOUR_BRIGHT, _COLOUR_MAGENTA, 0),
    "music": (_COLOUR_NORMAL, _COLOUR_RED, 0),
    "music_text": (_COLOUR_BRIGHT, _COLOUR_RED, 0),
    "question": (_COLOUR_BRIGHT, _COLOUR_YELLOW, 0),
    "question_text": (_COLOUR_BRIGHT, _COLOUR_WHITE, 0),
    "answer": (_COLOUR_BRIGHT, _COLOUR_YELLOW, 0),
    "answer_text": (_COLOUR_BRIGHT, _COLOUR_WHITE, 0),
    "quote": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "quote_text": (_COLOUR_BRIGHT, _COLOUR_GREEN, 0),
    "immtalk_text": (_COLOUR_NORMAL, _COLOUR_CYAN, 0),
    "immtalk_type": (_COLOUR_NORMAL, _COLOUR_YELLOW, 0),
    "info": (_COLOUR_NORMAL, _COLOUR_YELLOW, 1),
    "tell": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "tell_text": (_COLOUR_BRIGHT, _COLOUR_GREEN, 0),
    "reply": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "reply_text": (_COLOUR_BRIGHT, _COLOUR_GREEN, 0),
    "gtell_text": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "gtell_type": (_COLOUR_NORMAL, _COLOUR_RED, 0),
    "say": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "say_text": (_COLOUR_BRIGHT, _COLOUR_GREEN, 0),
    "wiznet": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "room_title": (_COLOUR_NORMAL, _COLOUR_CYAN, 0),
    "room_text": (_COLOUR_NORMAL, _COLOUR_WHITE, 0),
    "room_exits": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "room_things": (_COLOUR_NORMAL, _COLOUR_CYAN, 0),
    "prompt": (_COLOUR_NORMAL, _COLOUR_CYAN, 0),
    "fight_death": (_COLOUR_NORMAL, _COLOUR_RED, 0),
    "fight_yhit": (_COLOUR_NORMAL, _COLOUR_GREEN, 0),
    "fight_ohit": (_COLOUR_NORMAL, _COLOUR_YELLOW, 0),
    "fight_thit": (_COLOUR_NORMAL, _COLOUR_RED, 0),
    "fight_skill": (_COLOUR_NORMAL, _COLOUR_WHITE, 0),
}

PCDATA_COLOUR_FIELDS: tuple[str, ...] = (
    "text",
    "auction",
    "auction_text",
    "gossip",
    "gossip_text",
    "music",
    "music_text",
    "question",
    "question_text",
    "answer",
    "answer_text",
    "quote",
    "quote_text",
    "immtalk_text",
    "immtalk_type",
    "info",
    "tell",
    "tell_text",
    "reply",
    "reply_text",
    "gtell_text",
    "gtell_type",
    "say",
    "say_text",
    "wiznet",
    "room_title",
    "room_text",
    "room_exits",
    "room_things",
    "prompt",
    "fight_death",
    "fight_yhit",
    "fight_ohit",
    "fight_thit",
    "fight_skill",
)


def _default_colour_triplet(name: str) -> list[int]:
    base = _DEFAULT_PC_COLOUR_TABLE.get(name)
    if base is None:
        base = (_COLOUR_NORMAL, _COLOUR_WHITE, 0)
    return [base[0], base[1], base[2]]
