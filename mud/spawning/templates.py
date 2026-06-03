from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mud.models.object import Object

if TYPE_CHECKING:
    from mud.models.character import AffectData, Character, SpellEffect
    from mud.models.mob import MobIndex, MobProgram
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.models.room import Room

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    ImmFlag,
    MAX_STATS,
    OffFlag,
    Position,
    ResFlag,
    Sex,
    Size,
    STAT_CON,
    STAT_DEX,
    STAT_INT,
    STAT_STR,
    STAT_WIS,
    VulnFlag,
    attack_lookup,
    convert_flags_from_letters,
)
from mud.math.c_compat import c_div
from mud.utils import rng_mm


_DICE_RE = re.compile(r"^(\d+)d(\d+)(?:\+(-?\d+))?$")


def _parse_flags(raw: object, enum_type):
    """Return an IntFlag from ROM letter strings, IntFlag, or int."""

    if isinstance(raw, enum_type):
        return raw
    if isinstance(raw, int):
        return enum_type(raw)
    if isinstance(raw, str):
        return convert_flags_from_letters(raw, enum_type)
    return enum_type(0)


def _parse_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _parse_position(value: object, *, fallback: Position = Position.STANDING) -> Position:
    if isinstance(value, Position):
        return value
    if isinstance(value, int):
        try:
            return Position(value)
        except ValueError:
            return fallback
    if isinstance(value, str):
        normalized = value.strip().lower()
        mapping = {
            "dead": Position.DEAD,
            "mortal": Position.MORTAL,
            "incap": Position.INCAP,
            "incapacitated": Position.INCAP,
            "stun": Position.STUNNED,
            "stunned": Position.STUNNED,
            "sleep": Position.SLEEPING,
            "sleeping": Position.SLEEPING,
            "rest": Position.RESTING,
            "resting": Position.RESTING,
            "sit": Position.SITTING,
            "sitting": Position.SITTING,
            "fight": Position.FIGHTING,
            "fighting": Position.FIGHTING,
            "stand": Position.STANDING,
            "standing": Position.STANDING,
        }
        return mapping.get(normalized, fallback)
    return fallback


def _parse_sex(value: object) -> Sex:
    if isinstance(value, Sex):
        return value
    if isinstance(value, int):
        try:
            return Sex(value)
        except ValueError:
            return Sex.NONE
    if isinstance(value, str):
        mapping = {
            "neutral": Sex.NONE,
            "none": Sex.NONE,
            "male": Sex.MALE,
            "m": Sex.MALE,
            "female": Sex.FEMALE,
            "f": Sex.FEMALE,
            "either": Sex.EITHER,
        }
        return mapping.get(value.strip().lower(), Sex.NONE)
    return Sex.NONE


def _parse_size(value: object) -> Size:
    if isinstance(value, Size):
        return value
    if isinstance(value, int):
        try:
            return Size(value)
        except ValueError:
            return Size.MEDIUM
    if isinstance(value, str):
        mapping = {
            "tiny": Size.TINY,
            "small": Size.SMALL,
            "medium": Size.MEDIUM,
            "med": Size.MEDIUM,
            "large": Size.LARGE,
            "huge": Size.HUGE,
            "giant": Size.GIANT,
        }
        return mapping.get(value.strip().lower(), Size.MEDIUM)
    return Size.MEDIUM


def _parse_dice(primary: object, fallback: object) -> tuple[int, int, int]:
    if isinstance(primary, (tuple, list)) and len(primary) == 3:
        try:
            parsed = (int(primary[0]), int(primary[1]), int(primary[2]))
        except (TypeError, ValueError):
            parsed = None
        # Treat the all-zero tuple as "unset" and fall through to the string
        # fallback. JSON-loaded MobIndex prototypes leave the dice tuple at
        # its default and carry the actual value in ``hit_dice`` /
        # ``mana_dice`` / ``damage_dice`` strings.
        if parsed is not None and parsed != (0, 0, 0):
            return parsed
    if isinstance(fallback, str):
        match = _DICE_RE.match(fallback.strip())
        if match:
            number, size, bonus = match.groups()
            return (int(number), int(size), int(bonus or 0))
    if isinstance(primary, (tuple, list)) and len(primary) == 3:
        try:
            return (int(primary[0]), int(primary[1]), int(primary[2]))
        except (TypeError, ValueError):
            pass
    return (0, 0, 0)


def _roll_dice(dice_tuple: tuple[int, int, int]) -> int:
    number, size, bonus = dice_tuple
    if number <= 0 or size <= 0:
        return max(0, bonus)
    return max(0, rng_mm.dice(number, size) + bonus)


def _resolve_damage_type(value: object) -> int | None:
    """Resolve a mob damtype spec to a ROM attack_table INDEX (``ch->dam_type``).

    ROM stores ``pMobIndex->dam_type = attack_lookup(word)`` — an attack_table
    index, NOT a DamageType class (`src/db2.c:270`, `src/handler.c:165`). The
    damage *class* is derived at hit time from ``attack_table[index].damage``
    (`src/fight.c:431`) and the attack noun from ``attack_table[index].noun``
    (`src/fight.c:2176`). Collapsing the index to a class here was the
    FINDING-009 facet-2 bug (the drunk #3064 rendered "slice" instead of
    "beating"). Returns ``None`` when the spec is unusable so the caller can
    fall through to its next candidate.
    """

    if value is None:
        return None

    # An int is already an attack-table index (0 = none/unset). Mob protos never
    # carry a DamageType here (proto.dam_type is an int, proto.damage_type is the
    # raw .are word), so no DamageType special-casing is needed.
    if isinstance(value, int):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        # attack_lookup mirrors ROM: numeric strings return the index if in
        # range, name prefixes match the table, and anything unmatched (incl.
        # "none"/"hit"/"fire") returns 0 — which drives create_mobile's random
        # damtype roll. Do NOT fall back to DamageType[name]: a word that names a
        # DamageType but not an attack would resolve nonzero and silently
        # suppress the ROM number_range(1,3) roll (combat RNG-stream desync).
        return attack_lookup(normalized)

    return None


def _parse_damage_type(primary: object, fallback: object) -> int:
    for value in (primary, fallback):
        resolved = _resolve_damage_type(value)
        if resolved is None:
            continue
        if resolved != 0:
            return resolved
    return 0


@dataclass(eq=False)
class ObjectInstance:
    """Runtime instance of an object.

    ROM parity (INV-034 / divergence class 6): identity (`eq=False`) for the same
    reason as `Object`/`MobInstance`. Currently *not instantiated* anywhere (the
    live object spawn path is `spawn_object` → `mud.models.object.Object`); this
    is an entity-shaped legacy dataclass kept identity-eq so it can never become a
    value-equality landmine if revived. See
    ``docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`` INV-034.
    """

    name: str | None
    item_type: int
    prototype: ObjIndex
    short_descr: str | None = None
    location: Room | None = None
    contained_items: list[ObjectInstance] = field(default_factory=list)

    def move_to_room(self, room: Room) -> None:
        if self.location and hasattr(self.location, "contents"):
            if self in self.location.contents:
                self.location.contents.remove(self)
        room.contents.append(self)
        self.location = room


@dataclass(eq=False)
class MobInstance:
    """Runtime instance of a mob (NPC).

    ROM parity (INV-034 / divergence class 6): NPCs are compared by **pointer**.
    `MobInstance` is the live runtime type for mobs (`spawn_mob` returns it) and
    sits in `room.people` alongside `Character` PCs, so it uses ``eq=False`` for
    the same reason — ``__eq__``/``__hash__`` inherited from ``object`` (identity
    compare + identity hash). This is the **highest-risk** twin case: two
    same-vnum mobs spawned into a room have identical fields until combat mutates
    one, so value equality would make ``mob in room.people`` / ``room.people.
    remove(mob)`` confuse the two. See
    ``docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`` INV-034.
    """

    name: str | None
    level: int
    current_hp: int
    prototype: MobIndex
    max_hit: int = 0
    # ROM src/db.c:2040 create_mobile copies long_descr from the mob index; the
    # room listing (show_char_to_char_0) shows it for an NPC at its start_pos.
    long_descr: str | None = None
    # ROM create_mobile also copies description; show_char_to_char_1 (look <mob>)
    # shows it when non-empty.
    description: str | None = None
    inventory: list[Object] = field(default_factory=list)
    room: Room | None = None
    # Minimal encumbrance fields to interoperate with move_character
    carry_weight: int = 0
    carry_number: int = 0
    position: Position = Position.STANDING
    start_pos: Position = Position.STANDING
    default_pos: Position = Position.STANDING
    gold: int = 0
    silver: int = 0
    act: int = int(ActFlag.IS_NPC)
    affected_by: int = 0
    alignment: int = 0
    group: int = 0
    hitroll: int = 0
    damroll: int = 0
    damage: tuple[int, int, int] = (0, 0, 0)
    dam_type: int = 0
    armor: tuple[int, int, int, int] = (0, 0, 0, 0)
    # ROM CHAR_DATA.saving_throw is shared by PCs and NPCs (src/merc.h); saves_spell
    # reads victim->saving_throw for every target (src/magic.c:170). create_mobile
    # leaves it 0 for mobs (src/db.c — never set from the proto), so default 0.
    # Without this field, casting any saves_spell offensive spell at an NPC crashed
    # with AttributeError (FINDING-012, differential spell_combat scenario).
    saving_throw: int = 0
    off_flags: int = 0
    imm_flags: int = 0
    res_flags: int = 0
    vuln_flags: int = 0
    max_mana: int = 0
    mana: int = 0
    move: int = 100
    max_move: int = 100
    wait: int = 0
    sex: Sex = Sex.NONE
    size: Size = Size.MEDIUM
    form: int = 0
    parts: int = 0
    material: str | None = None
    race: str | int | None = None
    spec_fun: str | None = None
    mob_programs: list["MobProgram"] = field(default_factory=list)
    mprog_flags: int = 0
    mprog_target: "Character" | None = None
    mprog_delay: int = 0
    perm_stat: list[int] = field(default_factory=lambda: [0] * MAX_STATS)
    # GL-032: ROM stores affect stat modifiers in ch->mod_stat[] for PCs *and*
    # NPCs (src/handler.c:1072-1086 affect_modify), and get_curr_stat returns
    # perm_stat + mod_stat (src/handler.c:868-874). Mobs need their own mod_stat
    # so a buffed pet (giant strength etc.) actually gains the stat.
    mod_stat: list[int] = field(default_factory=lambda: [0] * MAX_STATS)
    comm: int = 0
    is_admin: bool = False
    is_npc: bool = True
    messages: list[str] = field(default_factory=list)
    fighting: "Character | MobInstance | None" = None  # Combat target
    pcdata: None = None  # NPCs don't have pcdata (player-specific data)
    spell_effects: dict[str, "SpellEffect"] = field(default_factory=dict)  # Active spell effects
    # GL-027: shadow AffectData mirror of spell_effects, so char_update ticks the
    # mob through ROM's main affect loop (src/update.c:762-786) instead of the
    # dict-only fallback (which rolled zero RNG and expired one tick early).
    affected: list[AffectData] = field(default_factory=list)

    @classmethod
    def from_prototype(cls, proto: MobIndex) -> MobInstance:
        wealth = getattr(proto, "wealth", 0) or 0
        gold_coins = 0
        silver_coins = 0
        act_flags = _parse_flags(getattr(proto, "act_flags", getattr(proto, "act", 0)), ActFlag)
        affect_flags = _parse_flags(getattr(proto, "affected_by", 0), AffectFlag)
        off_flags = _parse_flags(getattr(proto, "offensive", getattr(proto, "off_flags", 0)), OffFlag)
        imm_flags = _parse_flags(getattr(proto, "immune", getattr(proto, "imm_flags", 0)), ImmFlag)
        res_flags = _parse_flags(getattr(proto, "resist", getattr(proto, "res_flags", 0)), ResFlag)
        vuln_flags = _parse_flags(getattr(proto, "vuln", getattr(proto, "vuln_flags", 0)), VulnFlag)
        start_pos = _parse_position(getattr(proto, "start_pos", Position.STANDING))
        default_pos = _parse_position(getattr(proto, "default_pos", start_pos))
        sex = _parse_sex(getattr(proto, "sex", Sex.NONE))
        # NB: the random-sex roll (sex == EITHER) is deferred to the bottom of
        # this method — ROM create_mobile draws it LAST, after gold/hp/mana/damtype
        # (src/db.c:2107). Drawing it here would shift the RNG stream for every mob.
        size = _parse_size(getattr(proto, "size", Size.MEDIUM))
        level_value = _parse_int(getattr(proto, "level", 0))
        base_stat = min(25, 11 + c_div(level_value, 4))
        perm_stat = [base_stat for _ in range(MAX_STATS)]

        def adjust_stat(index: int, delta: int) -> None:
            perm_stat[index] += delta

        if act_flags & ActFlag.WARRIOR:
            adjust_stat(STAT_STR, 3)
            adjust_stat(STAT_INT, -1)
            adjust_stat(STAT_CON, 2)

        if act_flags & ActFlag.THIEF:
            adjust_stat(STAT_DEX, 3)
            adjust_stat(STAT_INT, 1)
            adjust_stat(STAT_WIS, -1)

        if act_flags & ActFlag.CLERIC:
            adjust_stat(STAT_WIS, 3)
            adjust_stat(STAT_DEX, -1)
            adjust_stat(STAT_STR, 1)

        if act_flags & ActFlag.MAGE:
            adjust_stat(STAT_INT, 3)
            adjust_stat(STAT_STR, -1)
            adjust_stat(STAT_DEX, 1)

        if off_flags & OffFlag.FAST:
            adjust_stat(STAT_DEX, 2)

        size_delta = int(size) - int(Size.MEDIUM)
        if size_delta:
            adjust_stat(STAT_STR, size_delta)
            adjust_stat(STAT_CON, c_div(size_delta, 2))
        form = _parse_int(getattr(proto, "form", 0))
        parts = _parse_int(getattr(proto, "parts", 0))
        material = getattr(proto, "material", None)
        damage_tuple = _parse_dice(getattr(proto, "damage", (0, 0, 0)), getattr(proto, "damage_dice", ""))
        dam_type_value = _parse_damage_type(getattr(proto, "dam_type", 0), getattr(proto, "damage_type", 0))
        hit_tuple = _parse_dice(getattr(proto, "hit", (0, 0, 0)), getattr(proto, "hit_dice", ""))
        mana_tuple = _parse_dice(getattr(proto, "mana", (0, 0, 0)), getattr(proto, "mana_dice", ""))
        armor = (
            _parse_int(getattr(proto, "ac_pierce", 0)),
            _parse_int(getattr(proto, "ac_bash", 0)),
            _parse_int(getattr(proto, "ac_slash", 0)),
            _parse_int(getattr(proto, "ac_exotic", 0)),
        )
        # RNG draw order MUST mirror ROM create_mobile (src/db.c:2047-2113) exactly,
        # because the spawn RNG stream is shared: gold -> hp -> mana -> damtype -> sex.
        # (Drawing in any other order shifts every subsequent mob's rolls vs ROM —
        # FINDING-007 / SPAWN-001: the drunk #3064 rolled HP 33 instead of ROM's 31.)
        # 1. gold/wealth (src/db.c:2047-2060)
        if wealth > 0:
            low = wealth // 2
            high = (3 * wealth) // 2
            if high < low:
                high = low
            total = rng_mm.number_range(low, high)
            gold_min = total // 200
            gold_max = max(total // 100, gold_min)
            if gold_max < gold_min:
                gold_max = gold_min
            gold_coins = rng_mm.number_range(gold_min, gold_max)
            silver_coins = max(total - gold_coins * 100, 0)
        # 2. HP dice, 3. mana dice (src/db.c:2074-2082)
        max_hit = _roll_dice(hit_tuple)
        max_mana = _roll_dice(mana_tuple)
        # 4. random damtype when unset (src/db.c:2086-2099). ROM assigns
        # attack-table INDICES 3/7/11 (slash/pound/pierce), NOT DamageType
        # classes — ch->dam_type is an attack_table index throughout, and
        # one_hit derives the damage class from attack_table[index].damage.
        if dam_type_value == 0:
            roll = rng_mm.number_range(1, 3)
            if roll == 1:
                dam_type_value = 3  # attack_table[3] = "slash" (DAM_SLASH)
            elif roll == 2:
                dam_type_value = 7  # attack_table[7] = "pound" (DAM_BASH)
            else:
                dam_type_value = 11  # attack_table[11] = "pierce" (DAM_PIERCE)
        # 5. random sex (src/db.c:2107) — drawn LAST, deferred from the parse above
        if sex == Sex.EITHER:
            sex = Sex(rng_mm.number_range(int(Sex.MALE), int(Sex.FEMALE)))
        max_move = 100
        default_comm = CommFlag.NOSHOUT | CommFlag.NOTELL | CommFlag.NOCHANNELS

        return cls(
            name=proto.short_descr or proto.player_name,
            level=level_value,
            current_hp=max_hit if max_hit else max(proto.hit[1] + proto.hit[2], 1),
            max_hit=max_hit,
            prototype=proto,
            long_descr=getattr(proto, "long_descr", None),  # ROM create_mobile (src/db.c:2040)
            description=getattr(proto, "description", None),  # ROM create_mobile (src/db.c)
            gold=gold_coins,
            silver=silver_coins,
            act=int(act_flags),
            affected_by=int(affect_flags),
            alignment=getattr(proto, "alignment", 0) or 0,
            group=getattr(proto, "group", 0) or 0,
            hitroll=getattr(proto, "hitroll", 0) or 0,
            damroll=damage_tuple[2],
            damage=damage_tuple,
            dam_type=dam_type_value,
            armor=armor,
            off_flags=int(off_flags),
            imm_flags=int(imm_flags),
            res_flags=int(res_flags),
            vuln_flags=int(vuln_flags),
            max_mana=max_mana,
            mana=max_mana,
            move=max_move,
            max_move=max_move,
            start_pos=start_pos,
            default_pos=default_pos,
            position=default_pos,
            sex=sex,
            size=size,
            form=form,
            parts=parts,
            material=material,
            race=getattr(proto, "race", None),
            spec_fun=getattr(proto, "spec_fun", None),
            mob_programs=list(getattr(proto, "mprogs", []) or []),
            mprog_flags=_parse_int(getattr(proto, "mprog_flags", 0)),
            mprog_target=None,
            mprog_delay=0,
            perm_stat=perm_stat,
            comm=int(default_comm),
        )

    def move_to_room(self, room: Room) -> None:
        if self.room and self in self.room.people:
            self.room.people.remove(self)
        room.people.append(self)
        self.room = room

    def add_to_inventory(self, obj: Object) -> None:
        if not any(existing is obj for existing in self.inventory):
            self.inventory.append(obj)
        obj.carried_by = self

    def remove_object(self, obj: Object) -> None:
        # ROM src/handler.c obj_from_char: unequip first if worn, then strip
        # from carried list. Mirror that here so disarm/remove paths actually
        # clear the equipment slot.
        if obj in self.inventory:
            self.inventory.remove(obj)
        else:
            equipment = getattr(self, "equipment", None)
            if isinstance(equipment, dict):
                for slot, eq in list(equipment.items()):
                    if eq is obj:
                        del equipment[slot]
                        break
        self.carry_number = max(0, self.carry_number - 1)

    def equip(self, obj: Object, slot: int) -> None:  # stub
        self.add_to_inventory(obj)
        obj.wear_loc = slot

    def get_curr_stat(self, stat: int) -> int:
        """
        Get current stat value for mob.

        ROM Parity: mirrors ROM ``get_curr_stat`` (src/handler.c:868-874) —
        ROM uses one function for PCs and NPCs, so a buffed mob (GL-032) reads
        ``perm_stat[stat] + mod_stat[stat]`` with the same lower clamp of 3
        used for player characters (GL-033).
        """
        if not hasattr(self, "perm_stat") or not self.perm_stat:
            return 13

        idx = int(stat)
        if idx < 0 or idx >= len(self.perm_stat):
            return 13

        mod = 0
        mod_stat = getattr(self, "mod_stat", None)
        if mod_stat and 0 <= idx < len(mod_stat):
            mod = int(mod_stat[idx] or 0)
        # mirroring ROM src/handler.c:868-874 get_curr_stat: NPCs use
        # URANGE(3, perm_stat + mod_stat, 25), not a Python-only zero floor.
        return max(3, min(25, self.perm_stat[idx] + mod))

    @property
    def hit(self) -> int:
        """Alias for current_hp to match Character interface."""
        return self.current_hp

    @hit.setter
    def hit(self, value: int) -> None:
        """Alias for current_hp to match Character interface."""
        self.current_hp = value

    def has_act_flag(self, flag: ActFlag) -> bool:
        act_bits = getattr(self, "act", 0)
        if act_bits:
            try:
                return bool(ActFlag(act_bits) & flag)
            except ValueError:
                return False
        proto = getattr(self, "prototype", None)
        if proto is None:
            return False
        checker = getattr(proto, "has_act_flag", None)
        if callable(checker):
            return bool(checker(flag))
        return False

    def has_affect(self, flag) -> bool:
        try:
            bit = int(flag)
        except Exception:
            return False
        return bool(getattr(self, "affected_by", 0) & bit)

    def has_spell_effect(self, name: str) -> bool:
        """Check if a named spell affect is active — ROM ``is_affected``
        equivalent, symmetric with ``Character.has_spell_effect`` so combat
        guards (e.g. ``do_berserk``'s ``is_affected(ch, gsn_berserk)``) work on a
        mob actor without crashing the game tick."""
        return name in self.spell_effects

    def is_awake(self) -> bool:
        """Mirror Character.is_awake (DUPL-010 consolidation)."""
        return self.position > Position.SLEEPING

    def add_affect(self, flag, **kwargs) -> None:
        """Apply an affect flag (simplified version for MobInstance)."""
        try:
            bit = int(flag)
        except Exception:
            return
        self.affected_by |= bit

    def _apply_stat_modifier(self, stat: int, delta: int) -> None:
        """Apply a delta to the mob's temporary ``mod_stat`` list (GL-032).

        Mirrors ``Character._apply_stat_modifier`` — ROM ``affect_modify``
        does ``ch->mod_stat[stat] += mod`` uniformly for PCs and NPCs
        (src/handler.c:1072-1086).
        """
        try:
            idx = int(stat)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            return
        if delta == 0:
            return
        mod_stat = getattr(self, "mod_stat", None)
        if not isinstance(mod_stat, list):
            self.mod_stat = mod_stat = [0] * MAX_STATS
        if len(mod_stat) < MAX_STATS:
            mod_stat.extend([0] * (MAX_STATS - len(mod_stat)))
        if idx < 0 or idx >= len(mod_stat):
            return
        mod_stat[idx] = int(mod_stat[idx] or 0) + delta

    def _shift_sex(self, delta: int) -> None:
        """Shift sex by ``delta``, clamped to the ROM ``Sex`` range (GL-032).

        Mirrors ``Character`` sex handling — ROM ``affect_modify`` does
        ``ch->sex += mod`` for APPLY_SEX (src/handler.c:1087-1088).
        """
        if not delta:
            return
        try:
            current = int(self.sex)
        except (TypeError, ValueError):
            current = 0
        new_sex = current + delta
        # Store an int, matching Character sex handling (the reload path also sets
        # pet.sex to an int from PetSave.sex), so live and reloaded pets agree.
        try:
            self.sex = int(Sex(new_sex))
        except (ValueError, TypeError):
            self.sex = max(0, min(new_sex, int(Sex.EITHER)))

    def remove_spell_effect(self, name: str) -> SpellEffect | None:
        """Remove a spell effect, unwinding every modifier that
        ``MobInstance.apply_spell_effect`` applied — ac / saving / stat / sex
        (GL-032) as well as hitroll / damroll / affect_flag — symmetric with
        ``Character.remove_spell_effect`` so the two paths never drift.

        GL-028: ``tick_spell_effects``'s dict-only fallback calls
        ``character.remove_spell_effect`` on expiry; ``MobInstance`` lacked
        this method, so an expiring mob spell effect raised ``AttributeError``
        out of ``char_update`` — aborting the whole game tick (no try/except
        guards the per-character loop or the ``char_update()`` call).
        """
        effect = self.spell_effects.pop(name, None)
        if effect is None:
            return None
        # GL-032: unwind APPLY_AC across all four armor classes (mirroring ROM
        # affect_modify, src/handler.c:1113-1116). armor is a tuple — rebuild it.
        if getattr(effect, "ac_mod", 0):
            self.armor = tuple(ac - effect.ac_mod for ac in self.armor)
        if getattr(effect, "hitroll_mod", 0):
            self.hitroll -= effect.hitroll_mod
        if getattr(effect, "damroll_mod", 0):
            self.damroll -= effect.damroll_mod
        if getattr(effect, "saving_throw_mod", 0):
            self.saving_throw -= effect.saving_throw_mod
        if getattr(effect, "affect_flag", None) is not None:
            try:
                self.affected_by &= ~int(effect.affect_flag)
            except Exception:
                pass
        stat_mods = getattr(effect, "stat_modifiers", None)
        if isinstance(stat_mods, dict):
            for stat, delta in stat_mods.items():
                self._apply_stat_modifier(stat, -int(delta))
        self._shift_sex(-int(getattr(effect, "sex_delta", 0) or 0))
        # GL-027: drop the shadow AffectData mirror so the main tick path
        # (mud/affects/engine.py) doesn't keep ticking a removed effect.
        self.affected = [paf for paf in self.affected if getattr(paf, "type", None) != name]
        return effect

    def apply_spell_effect(self, effect: "SpellEffect") -> bool:
        """Apply a spell effect to a mob, at full parity with
        ``Character.apply_spell_effect`` — every ROM ``affect_modify`` location
        (ac / saving / stat / sex / hitroll / damroll / affect_flag), since ROM
        applies them uniformly to NPCs and PCs (src/handler.c:1018-1164). GL-032.
        """
        from dataclasses import replace
        from mud.math.c_compat import c_div
        from mud.models.character import sync_spell_effect_to_affected

        existing = self.spell_effects.get(effect.name)
        combined = replace(effect)
        combined.stat_modifiers = dict(combined.stat_modifiers or {})
        combined.sex_delta = int(getattr(combined, "sex_delta", 0) or 0)

        if existing is not None:
            combined.level = c_div(combined.level + existing.level, 2)
            combined.duration += existing.duration
            combined.ac_mod += existing.ac_mod
            combined.hitroll_mod += existing.hitroll_mod
            combined.damroll_mod += existing.damroll_mod
            combined.saving_throw_mod += existing.saving_throw_mod
            if combined.affect_flag is None:
                combined.affect_flag = existing.affect_flag
            for stat, delta in getattr(existing, "stat_modifiers", {}).items():
                combined.stat_modifiers[stat] = combined.stat_modifiers.get(stat, 0) + int(delta)
            combined.sex_delta += int(getattr(existing, "sex_delta", 0) or 0)
            # ROM affect_join replaces the prior affect: remove it (its applied
            # mods AND its shadow AffectData) before applying the merged one, so
            # a re-cast neither double-applies nor leaves a duplicate shadow on
            # self.affected. Mirrors Character.apply_spell_effect.
            self.remove_spell_effect(effect.name)

        # Apply every affect location (GL-032) — mirrors ROM affect_modify.
        if combined.ac_mod:
            self.armor = tuple(ac + combined.ac_mod for ac in self.armor)
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
        self._shift_sex(combined.sex_delta)

        self.spell_effects[combined.name] = combined
        # GL-027: mirror shadow AffectData into self.affected so char_update ticks
        # the mob through ROM's main affect loop (one number_range roll per
        # duration>0 affect, decrement-and-stay) instead of the dict-only fallback.
        sync_spell_effect_to_affected(self, combined)
        return True

    def is_immortal(self) -> bool:
        return False
