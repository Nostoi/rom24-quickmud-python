from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mud.models.object import Object

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.mob import MobIndex, MobProgram
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.models.room import Room

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    DamageType,
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
    attack_damage_type,
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
            return (int(primary[0]), int(primary[1]), int(primary[2]))
        except (TypeError, ValueError):
            pass
    if isinstance(fallback, str):
        match = _DICE_RE.match(fallback.strip())
        if match:
            number, size, bonus = match.groups()
            return (int(number), int(size), int(bonus or 0))
    return (0, 0, 0)


def _roll_dice(dice_tuple: tuple[int, int, int]) -> int:
    number, size, bonus = dice_tuple
    if number <= 0 or size <= 0:
        return max(0, bonus)
    return max(0, rng_mm.dice(number, size) + bonus)


def _resolve_damage_type(value: object) -> int | None:
    """Translate ROM attack indices, enum names, or direct values to DamageType."""

    if value is None:
        return None

    if isinstance(value, DamageType):
        return int(value)

    if isinstance(value, int):
        if value == 0:
            return 0
        damage_enum = attack_damage_type(value)
        if damage_enum is not None:
            return int(damage_enum)
        try:
            enum_value = DamageType(value)
        except ValueError:
            return None
        return int(enum_value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in {"0", "none", "hit"}:
            return 0
        if normalized.isdigit():
            return _resolve_damage_type(int(normalized))
        attack_index = attack_lookup(normalized)
        if attack_index:
            damage_enum = attack_damage_type(attack_index)
            if damage_enum is not None:
                return int(damage_enum)
        try:
            enum_value = DamageType[normalized.upper()]
        except KeyError:
            return None
        return int(enum_value)

    return None


def _parse_damage_type(primary: object, fallback: object) -> int:
    for value in (primary, fallback):
        resolved = _resolve_damage_type(value)
        if resolved is None:
            continue
        if resolved != 0:
            return resolved
    return 0


@dataclass
class ObjectInstance:
    """Runtime instance of an object."""

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


@dataclass
class MobInstance:
    """Runtime instance of a mob (NPC)."""

    name: str | None
    level: int
    current_hp: int
    prototype: MobIndex
    max_hit: int = 0
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
    comm: int = 0
    is_admin: bool = False
    is_npc: bool = True
    messages: list[str] = field(default_factory=list)
    fighting: "Character | MobInstance | None" = None  # Combat target

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
        if sex == Sex.EITHER:
            sex = Sex(rng_mm.number_range(int(Sex.MALE), int(Sex.FEMALE)))
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
        damage_tuple = _parse_dice(
            getattr(proto, "damage", (0, 0, 0)), getattr(proto, "damage_dice", "")
        )
        dam_type_value = _parse_damage_type(getattr(proto, "dam_type", 0), getattr(proto, "damage_type", 0))
        if dam_type_value == 0:
            roll = rng_mm.number_range(1, 3)
            if roll == 1:
                dam_type_value = int(DamageType.SLASH)
            elif roll == 2:
                dam_type_value = int(DamageType.BASH)
            else:
                dam_type_value = int(DamageType.PIERCE)
        hit_tuple = _parse_dice(getattr(proto, "hit", (0, 0, 0)), getattr(proto, "hit_dice", ""))
        mana_tuple = _parse_dice(getattr(proto, "mana", (0, 0, 0)), getattr(proto, "mana_dice", ""))
        max_hit = _roll_dice(hit_tuple)
        max_mana = _roll_dice(mana_tuple)
        armor = (
            _parse_int(getattr(proto, "ac_pierce", 0)),
            _parse_int(getattr(proto, "ac_bash", 0)),
            _parse_int(getattr(proto, "ac_slash", 0)),
            _parse_int(getattr(proto, "ac_exotic", 0)),
        )
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
        max_move = 100
        default_comm = CommFlag.NOSHOUT | CommFlag.NOTELL | CommFlag.NOCHANNELS

        return cls(
            name=proto.short_descr or proto.player_name,
            level=level_value,
            current_hp=max_hit if max_hit else max(proto.hit[1] + proto.hit[2], 1),
            max_hit=max_hit,
            prototype=proto,
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
        obj.location = None

    def equip(self, obj: Object, slot: int) -> None:  # stub
        self.add_to_inventory(obj)
        obj.wear_loc = slot

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

    def is_immortal(self) -> bool:
        return False
