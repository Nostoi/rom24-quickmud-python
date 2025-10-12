from __future__ import annotations

# Auto-generated skill handlers
# TODO: Replace stubs with actual ROM spell/skill implementations
from types import SimpleNamespace

from mud.affects.saves import check_dispel, saves_dispel, saves_spell
from mud.combat.engine import (
    apply_damage,
    attack_round,
    get_wielded_weapon,
    get_weapon_skill,
    get_weapon_sn,
    is_evil,
    is_good,
    is_neutral,
    set_fighting,
    stop_fighting,
    update_pos,
)
from mud.game_loop import SkyState, weather
from mud.characters import is_clan_member, is_same_clan, is_same_group
from mud.characters.follow import add_follower, stop_follower
from mud.magic.effects import (
    SpellTarget,
    acid_effect,
    cold_effect,
    fire_effect,
    poison_effect,
    shock_effect,
)
from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import (
    AffectFlag,
    ActFlag,
    ContainerFlag,
    DamageType,
    ExtraFlag,
    OffFlag,
    ImmFlag,
    ItemType,
    LIQUID_TABLE,
    Sector,
    PlayerFlag,
    Position,
    ResFlag,
    RoomFlag,
    Sex,
    Stat,
    VulnFlag,
    WearLocation,
    WeaponFlag,
    WeaponType,
    LEVEL_HERO,
    LEVEL_IMMORTAL,
    LIQ_WATER,
    OBJ_VNUM_DISC,
    OBJ_VNUM_LIGHT_BALL,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_ROSE,
    OBJ_VNUM_SPRING,
    ROOM_VNUM_TEMPLE,
)
from mud.models.object import Object
from mud.models.obj import Affect, ObjectData
from mud.net.protocol import broadcast_room
from mud.spawning.obj_spawner import spawn_object
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world.look import look
from mud.world.movement import _get_random_room
from mud.world.vision import can_see_room

from mud.skills.metadata import ROM_SKILL_METADATA, ROM_SKILL_NAMES_BY_INDEX
from mud.skills.registry import check_improve


# ROM const.c lists "spell" as the noun_damage for the cause harm trio.
_CAUSE_SPELL_ATTACK_NOUN = "spell"


_TO_AFFECTS = 0
_TO_OBJECT = 1
_TO_IMMUNE = 2
_TO_RESIST = 3
_TO_VULN = 4
_TO_WEAPON = 5
_APPLY_NONE = 0
_OBJECT_INVIS_WEAR_OFF = "$p fades into view."
_OBJECT_FIREPROOF_WEAR_OFF = "$p's protective aura fades."


def _flag_names(value: int, mapping: tuple[tuple[int, str], ...]) -> str:
    names: list[str] = []
    for bit, label in mapping:
        if value & bit:
            names.append(label)
    return " ".join(names) if names else "none"


def _item_type_name(raw_type: object) -> str:
    item_type = _resolve_item_type(raw_type)
    if item_type is None:
        return "unknown"
    return _ITEM_TYPE_NAMES.get(item_type, item_type.name.lower())


def _weapon_type_name(raw_type: int) -> str:
    try:
        weapon_type = WeaponType(int(raw_type))
    except (TypeError, ValueError):
        return "unknown"
    return _WEAPON_TYPE_NAMES.get(weapon_type, "exotic")


def _extra_bit_name(flags: int) -> str:
    return _flag_names(flags, _EXTRA_FLAG_LABELS)


def _container_flag_name(flags: int) -> str:
    return _flag_names(flags, _CONTAINER_FLAG_LABELS)


def _affect_loc_name(location: int) -> str:
    return _AFFECT_LOCATION_NAMES.get(location, "(unknown)")


def _affect_bit_name(bitvector: int) -> str:
    return _flag_names(bitvector, _AFFECT_FLAG_LABELS)


def _imm_bit_name(bitvector: int) -> str:
    return _flag_names(bitvector, _IMMUNITY_LABELS)


def _weapon_bit_name(bitvector: int) -> str:
    return _flag_names(bitvector, _WEAPON_FLAG_LABELS)


def _skill_name_from_value(raw_value: int) -> str | None:
    if raw_value < 0:
        return None
    if raw_value >= len(ROM_SKILL_NAMES_BY_INDEX):
        return None
    return ROM_SKILL_NAMES_BY_INDEX[raw_value]


def _lookup_liquid(index: int):
    if 0 <= index < len(LIQUID_TABLE):
        return LIQUID_TABLE[index]
    return LIQUID_TABLE[LIQ_WATER]


def _skill_percent(character: Character, name: str) -> int:
    """Return the learned percentage for a skill name (0-100 clamp)."""

    skills = getattr(character, "skills", {}) or {}
    if not isinstance(skills, dict):
        return 0
    try:
        value = skills.get(name, 0)
        percent = int(value or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        percent = 0
    return max(0, min(100, percent))


def _skill_beats(name: str) -> int:
    """Lookup ROM beat/lag values for a skill with a safe default."""

    metadata = ROM_SKILL_METADATA.get(name, {})
    try:
        beats = int(metadata.get("beats", 0))
    except (TypeError, ValueError):
        beats = 0
    return beats if beats > 0 else 12


def _resolve_weight(obj: Object | ObjectData | object) -> int:
    raw_weight = getattr(obj, "weight", 0)
    if not raw_weight:
        proto = getattr(obj, "prototype", None)
        raw_weight = getattr(proto, "weight", 0)
    return c_div(_coerce_int(raw_weight), 10)


def _resolve_cost(obj: Object | ObjectData | object) -> int:
    cost = getattr(obj, "cost", None)
    if cost is None or (isinstance(cost, int) and cost == 0):
        proto = getattr(obj, "prototype", None)
        cost = getattr(proto, "cost", 0) if proto is not None else 0
    return _coerce_int(cost)


def _resolve_level(obj: Object | ObjectData | object) -> int:
    level = getattr(obj, "level", None)
    if level is None or (isinstance(level, int) and level == 0):
        proto = getattr(obj, "prototype", None)
        level = getattr(proto, "level", 0) if proto is not None else 0
    return _coerce_int(level)


def _iter_prototype_affects(obj: Object | ObjectData | object):
    prototype = getattr(obj, "prototype", None)
    if prototype is None:
        return
    if getattr(obj, "enchanted", False):
        return
    for entry in getattr(prototype, "affected", []) or []:
        yield entry
    for entry in getattr(prototype, "affects", []) or []:
        yield entry


def _coerce_affect(entry: object) -> SimpleNamespace | Affect:
    if isinstance(entry, Affect):
        return entry
    if isinstance(entry, dict):
        return SimpleNamespace(
            where=_coerce_int(entry.get("where", _TO_OBJECT)),
            level=_coerce_int(entry.get("level", 0)),
            duration=_coerce_int(entry.get("duration", -1)),
            location=_coerce_int(entry.get("location", _APPLY_NONE)),
            modifier=_coerce_int(entry.get("modifier", 0)),
            bitvector=_coerce_int(entry.get("bitvector", 0)),
        )
    return SimpleNamespace(
        where=_coerce_int(getattr(entry, "where", _TO_OBJECT)),
        level=_coerce_int(getattr(entry, "level", 0)),
        duration=_coerce_int(getattr(entry, "duration", -1)),
        location=_coerce_int(getattr(entry, "location", _APPLY_NONE)),
        modifier=_coerce_int(getattr(entry, "modifier", 0)),
        bitvector=_coerce_int(getattr(entry, "bitvector", 0)),
    )


def _iter_all_affects(obj: Object | ObjectData | object):
    for entry in _iter_prototype_affects(obj) or []:
        yield _coerce_affect(entry)
    for entry in getattr(obj, "affected", []) or []:
        yield _coerce_affect(entry)


def _emit_affect_descriptions(caster: Character, obj: Object | ObjectData | object) -> None:
    for affect in _iter_all_affects(obj):
        location_name = _affect_loc_name(int(getattr(affect, "location", _APPLY_NONE)))
        modifier = _coerce_int(getattr(affect, "modifier", 0))
        duration = _coerce_int(getattr(affect, "duration", -1))
        base = f"Affects {location_name} by {modifier}"
        if duration > -1:
            base = f"{base}, {duration} hours."
        else:
            base = f"{base}."
        _send_to_char(caster, base)

        bitvector = _coerce_int(getattr(affect, "bitvector", 0))
        if not bitvector:
            continue
        where = _coerce_int(getattr(affect, "where", _TO_OBJECT))
        if where == _TO_AFFECTS:
            descriptor = _affect_bit_name(bitvector)
            if descriptor:
                _send_to_char(caster, f"Adds {descriptor} affect.")
        elif where == _TO_OBJECT:
            descriptor = _extra_bit_name(bitvector)
            if descriptor:
                _send_to_char(caster, f"Adds {descriptor} object flag.")
        elif where == _TO_IMMUNE:
            descriptor = _imm_bit_name(bitvector)
            _send_to_char(caster, f"Adds immunity to {descriptor}.")
        elif where == _TO_RESIST:
            descriptor = _imm_bit_name(bitvector)
            _send_to_char(caster, f"Adds resistance to {descriptor}.")
        elif where == _TO_VULN:
            descriptor = _imm_bit_name(bitvector)
            _send_to_char(caster, f"Adds vulnerability to {descriptor}.")
        elif where == _TO_WEAPON:
            descriptor = _weapon_bit_name(bitvector)
            _send_to_char(caster, f"Adds {descriptor} weapon flags.")
        else:
            _send_to_char(caster, f"Unknown bit {where}: {bitvector}")

_ITEM_TYPE_NAMES: dict[ItemType, str] = {
    ItemType.SCROLL: "scroll",
    ItemType.WAND: "wand",
    ItemType.STAFF: "staff",
    ItemType.WEAPON: "weapon",
    ItemType.TREASURE: "treasure",
    ItemType.ARMOR: "armor",
    ItemType.POTION: "potion",
    ItemType.CLOTHING: "clothing",
    ItemType.FURNITURE: "furniture",
    ItemType.TRASH: "trash",
    ItemType.CONTAINER: "container",
    ItemType.DRINK_CON: "drink",
    ItemType.KEY: "key",
    ItemType.FOOD: "food",
    ItemType.MONEY: "money",
    ItemType.BOAT: "boat",
    ItemType.CORPSE_NPC: "npc_corpse",
    ItemType.CORPSE_PC: "pc_corpse",
    ItemType.FOUNTAIN: "fountain",
    ItemType.PILL: "pill",
    ItemType.PROTECT: "protect",
    ItemType.MAP: "map",
    ItemType.PORTAL: "portal",
    ItemType.WARP_STONE: "warp_stone",
    ItemType.ROOM_KEY: "room_key",
    ItemType.GEM: "gem",
    ItemType.JEWELRY: "jewelry",
    ItemType.JUKEBOX: "jukebox",
}

_WEAPON_TYPE_NAMES: dict[WeaponType, str] = {
    WeaponType.EXOTIC: "exotic",
    WeaponType.SWORD: "sword",
    WeaponType.DAGGER: "dagger",
    WeaponType.SPEAR: "spear/staff",
    WeaponType.MACE: "mace/club",
    WeaponType.AXE: "axe",
    WeaponType.FLAIL: "flail",
    WeaponType.WHIP: "whip",
    WeaponType.POLEARM: "polearm",
}

_EXTRA_FLAG_LABELS: tuple[tuple[int, str], ...] = (
    (int(ExtraFlag.GLOW), "glow"),
    (int(ExtraFlag.HUM), "hum"),
    (int(ExtraFlag.DARK), "dark"),
    (int(ExtraFlag.LOCK), "lock"),
    (int(ExtraFlag.EVIL), "evil"),
    (int(ExtraFlag.INVIS), "invis"),
    (int(ExtraFlag.MAGIC), "magic"),
    (int(ExtraFlag.NODROP), "nodrop"),
    (int(ExtraFlag.BLESS), "bless"),
    (int(ExtraFlag.ANTI_GOOD), "anti-good"),
    (int(ExtraFlag.ANTI_EVIL), "anti-evil"),
    (int(ExtraFlag.ANTI_NEUTRAL), "anti-neutral"),
    (int(ExtraFlag.NOREMOVE), "noremove"),
    (int(ExtraFlag.INVENTORY), "inventory"),
    (int(ExtraFlag.NOPURGE), "nopurge"),
    (int(ExtraFlag.VIS_DEATH), "vis_death"),
    (int(ExtraFlag.ROT_DEATH), "rot_death"),
    (int(ExtraFlag.NOLOCATE), "no_locate"),
    (int(ExtraFlag.SELL_EXTRACT), "sell_extract"),
    (int(ExtraFlag.BURN_PROOF), "burn_proof"),
    (int(ExtraFlag.NOUNCURSE), "no_uncurse"),
)

_CONTAINER_FLAG_LABELS: tuple[tuple[int, str], ...] = (
    (int(ContainerFlag.CLOSEABLE), "closable"),
    (int(ContainerFlag.PICKPROOF), "pickproof"),
    (int(ContainerFlag.CLOSED), "closed"),
    (int(ContainerFlag.LOCKED), "locked"),
    (int(ContainerFlag.PUT_ON), "put_on"),
)

_AFFECT_LOCATION_NAMES: dict[int, str] = {
    0: "none",
    1: "strength",
    2: "dexterity",
    3: "intelligence",
    4: "wisdom",
    5: "constitution",
    6: "sex",
    7: "class",
    8: "level",
    9: "age",
    10: "height",
    11: "weight",
    12: "mana",
    13: "hp",
    14: "moves",
    15: "gold",
    16: "experience",
    17: "armor class",
    18: "hit roll",
    19: "damage roll",
    20: "saves",
    21: "save vs rod",
    22: "save vs petrification",
    23: "save vs breath",
    24: "save vs spell",
    25: "none",
}

_AFFECT_FLAG_LABELS: tuple[tuple[int, str], ...] = (
    (int(AffectFlag.BLIND), "blind"),
    (int(AffectFlag.INVISIBLE), "invisible"),
    (int(AffectFlag.DETECT_EVIL), "detect_evil"),
    (int(AffectFlag.DETECT_GOOD), "detect_good"),
    (int(AffectFlag.DETECT_INVIS), "detect_invis"),
    (int(AffectFlag.DETECT_MAGIC), "detect_magic"),
    (int(AffectFlag.DETECT_HIDDEN), "detect_hidden"),
    (int(AffectFlag.SANCTUARY), "sanctuary"),
    (int(AffectFlag.FAERIE_FIRE), "faerie_fire"),
    (int(AffectFlag.INFRARED), "infrared"),
    (int(AffectFlag.CURSE), "curse"),
    (int(AffectFlag.POISON), "poison"),
    (int(AffectFlag.PROTECT_EVIL), "prot_evil"),
    (int(AffectFlag.PROTECT_GOOD), "prot_good"),
    (int(AffectFlag.SLEEP), "sleep"),
    (int(AffectFlag.SNEAK), "sneak"),
    (int(AffectFlag.HIDE), "hide"),
    (int(AffectFlag.CHARM), "charm"),
    (int(AffectFlag.FLYING), "flying"),
    (int(AffectFlag.PASS_DOOR), "pass_door"),
    (int(AffectFlag.BERSERK), "berserk"),
    (int(AffectFlag.CALM), "calm"),
    (int(AffectFlag.HASTE), "haste"),
    (int(AffectFlag.SLOW), "slow"),
    (int(AffectFlag.PLAGUE), "plague"),
    (int(AffectFlag.DARK_VISION), "dark_vision"),
)

_IMMUNITY_LABELS: tuple[tuple[int, str], ...] = (
    (int(ImmFlag.SUMMON), "summon"),
    (int(ImmFlag.CHARM), "charm"),
    (int(ImmFlag.MAGIC), "magic"),
    (int(ImmFlag.WEAPON), "weapon"),
    (int(ImmFlag.BASH), "blunt"),
    (int(ImmFlag.PIERCE), "piercing"),
    (int(ImmFlag.SLASH), "slashing"),
    (int(ImmFlag.FIRE), "fire"),
    (int(ImmFlag.COLD), "cold"),
    (int(ImmFlag.LIGHTNING), "lightning"),
    (int(ImmFlag.ACID), "acid"),
    (int(ImmFlag.POISON), "poison"),
    (int(ImmFlag.NEGATIVE), "negative"),
    (int(ImmFlag.HOLY), "holy"),
    (int(ImmFlag.ENERGY), "energy"),
    (int(ImmFlag.MENTAL), "mental"),
    (int(ImmFlag.DISEASE), "disease"),
    (int(ImmFlag.DROWNING), "drowning"),
    (int(ImmFlag.LIGHT), "light"),
    (int(VulnFlag.IRON), "iron"),
    (int(VulnFlag.WOOD), "wood"),
    (int(VulnFlag.SILVER), "silver"),
)

_WEAPON_FLAG_LABELS: tuple[tuple[int, str], ...] = (
    (int(WeaponFlag.FLAMING), "flaming"),
    (int(WeaponFlag.FROST), "frost"),
    (int(WeaponFlag.VAMPIRIC), "vampiric"),
    (int(WeaponFlag.SHARP), "sharp"),
    (int(WeaponFlag.VORPAL), "vorpal"),
    (int(WeaponFlag.TWO_HANDS), "two-handed"),
    (int(WeaponFlag.SHOCKING), "shocking"),
    (int(WeaponFlag.POISON), "poison"),
)


def _send_to_char(character: Character, message: str) -> None:
    """Append a message to the character similar to ROM send_to_char."""

    if hasattr(character, "send_to_char"):
        try:
            character.send_to_char(message)
            return
        except Exception:  # pragma: no cover - defensive parity guard
            pass
    if hasattr(character, "messages"):
        character.messages.append(message)


def _is_outside(character: Character) -> bool:
    """Return True when the character is in a room without ROOM_INDOORS."""

    room = getattr(character, "room", None)
    if room is None:
        return False
    try:
        flags = int(getattr(room, "room_flags", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - invalid flags fall back
        flags = 0
    return not bool(flags & int(RoomFlag.ROOM_INDOORS))


def _normalize_value_list(obj: Object, *, minimum: int = 3) -> list[int]:
    """Return a mutable copy of an object's value list with at least ``minimum`` slots."""

    raw_values = getattr(obj, "value", None)
    if isinstance(raw_values, list):
        values = list(raw_values)
    else:
        values = []
    if len(values) < minimum:
        values.extend([0] * (minimum - len(values)))
    return values


def _coerce_int(value: object) -> int:
    """Best-effort conversion mirroring ROM's permissive int coercion."""

    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_item_type(value: object) -> ItemType | None:
    """Translate assorted item type representations to ``ItemType``."""

    if isinstance(value, ItemType):
        return value
    if isinstance(value, int):
        try:
            return ItemType(value)
        except ValueError:
            return None
    if isinstance(value, str):
        normalized = value.strip().replace(" ", "_").replace("-", "_").upper()
        if not normalized:
            return None
        aliases = {
            "DRINK": ItemType.DRINK_CON,
            "DRINKCON": ItemType.DRINK_CON,
            "DRINK_CONTAINER": ItemType.DRINK_CON,
            "DRINK_CON": ItemType.DRINK_CON,
        }
        item = aliases.get(normalized)
        if item is not None:
            return item
        try:
            return ItemType[normalized]
        except KeyError:
            return None
    return None


def _object_short_descr(obj: Object | ObjectData) -> str:
    """Return a user-facing short description for messaging."""

    short_descr = getattr(obj, "short_descr", None)
    if isinstance(short_descr, str) and short_descr.strip():
        return short_descr.strip()
    short_descr = getattr(getattr(obj, "prototype", None), "short_descr", None)
    if isinstance(short_descr, str) and short_descr.strip():
        return short_descr.strip()
    return "Something"


def _character_name(character: Character | None) -> str:
    """Return the character's display name or a fallback placeholder."""

    if character is None:
        return "Someone"
    name = getattr(character, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    short_descr = getattr(character, "short_descr", None)
    if isinstance(short_descr, str) and short_descr.strip():
        return short_descr.strip()
    return "Someone"


def _reflexive_pronoun(character: Character | None) -> str:
    """Return a reflexive pronoun matching the character's sex."""

    try:
        sex = Sex(int(getattr(character, "sex", 0) or 0))
    except (TypeError, ValueError):
        return "themselves"

    return {
        Sex.MALE: "himself",
        Sex.FEMALE: "herself",
        Sex.NONE: "itself",
    }.get(sex, "themselves")


def _possessive_pronoun(character: Character | None) -> str:
    """Return a possessive pronoun (his/her/its/their) for messaging."""

    try:
        sex = Sex(int(getattr(character, "sex", 0) or 0))
    except (TypeError, ValueError):
        return "their"

    return {
        Sex.MALE: "his",
        Sex.FEMALE: "her",
        Sex.NONE: "its",
    }.get(sex, "their")


def _get_room_flags(room) -> int:
    try:
        return int(getattr(room, "room_flags", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return 0


def _get_act_flags(character: Character | object) -> ActFlag:
    """Best-effort conversion of runtime act flags for NPC safety checks."""

    flags = 0
    for source in (
        getattr(character, "act", 0),
        getattr(character, "act_flags", 0),
        getattr(getattr(character, "prototype", None), "act", 0),
        getattr(getattr(character, "prototype", None), "act_flags", 0),
        getattr(getattr(character, "pIndexData", None), "act", 0),
        getattr(getattr(character, "pIndexData", None), "act_flags", 0),
    ):
        if source is None:
            continue
        if isinstance(source, ActFlag):
            flags |= int(source)
            continue
        try:
            flags |= int(source)
        except (TypeError, ValueError):  # pragma: no cover - defensive fallback
            continue
    try:
        return ActFlag(flags)
    except ValueError:  # pragma: no cover - invalid bits default to 0
        return ActFlag(0)


def _get_player_flags(character: Character) -> PlayerFlag:
    if getattr(character, "is_npc", True):
        return PlayerFlag(0)
    try:
        return PlayerFlag(int(getattr(character, "act", 0) or 0))
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return PlayerFlag(0)


def _has_shop(character: Character) -> bool:
    for source in (
        getattr(character, "pShop", None),
        getattr(getattr(character, "prototype", None), "pShop", None),
        getattr(getattr(character, "pIndexData", None), "pShop", None),
        getattr(character, "shop", None),
    ):
        if source is not None:
            return True
    return False


def _is_charmed(character: Character) -> bool:
    return character.has_affect(AffectFlag.CHARM) if hasattr(character, "has_affect") else False


def _is_safe_spell(caster: Character, victim: Character, *, area: bool) -> bool:
    """Mirror ROM ``is_safe_spell`` safeguards for area spells."""

    if caster is None or victim is None:
        return True

    victim_room = getattr(victim, "room", None)
    caster_room = getattr(caster, "room", None)
    if victim_room is None or caster_room is None:
        return True

    if area and victim is caster:
        return True

    if getattr(victim, "fighting", None) is caster or victim is caster:
        return False

    if hasattr(caster, "is_immortal") and caster.is_immortal() and getattr(caster, "level", 0) > LEVEL_IMMORTAL and not area:
        return False

    victim_is_npc = bool(getattr(victim, "is_npc", True))
    caster_is_npc = bool(getattr(caster, "is_npc", True))

    if victim_is_npc:
        if _get_room_flags(victim_room) & int(RoomFlag.ROOM_SAFE):
            return True
        if _has_shop(victim):
            return True

        act_flags = _get_act_flags(victim)
        if act_flags & (ActFlag.TRAIN | ActFlag.PRACTICE | ActFlag.IS_HEALER | ActFlag.IS_CHANGER):
            return True

        if not caster_is_npc:
            if act_flags & ActFlag.PET:
                return True
            if _is_charmed(victim) and (area or getattr(victim, "master", None) is not caster):
                return True
            victim_fighting = getattr(victim, "fighting", None)
            if victim_fighting is not None and not is_same_group(caster, victim_fighting):
                return True
        else:
            if area:
                caster_fighting = getattr(caster, "fighting", None)
                if not is_same_group(victim, caster_fighting):
                    return True
    else:
        if area and hasattr(victim, "is_immortal") and victim.is_immortal() and getattr(victim, "level", 0) > LEVEL_IMMORTAL:
            return True

        if caster_is_npc:
            if _is_charmed(caster):
                master = getattr(caster, "master", None)
                if master is not None and getattr(master, "fighting", None) is not victim:
                    return True
            if _get_room_flags(victim_room) & int(RoomFlag.ROOM_SAFE):
                return True
            caster_fighting = getattr(caster, "fighting", None)
            if caster_fighting is not None and not is_same_group(caster_fighting, victim):
                return True
        else:
            if not is_clan_member(caster):
                return True
            player_flags = _get_player_flags(victim)
            if player_flags & (PlayerFlag.KILLER | PlayerFlag.THIEF):
                return False
            if not is_clan_member(victim):
                return True
            caster_level = _coerce_int(getattr(caster, "level", 0))
            victim_level = _coerce_int(getattr(victim, "level", 0))
            if caster_level > victim_level + 8:
                return True

    return False


def _breath_damage(
    caster: Character,
    level: int,
    *,
    min_hp: int,
    low_divisor: int,
    high_divisor: int,
    dice_size: int,
    high_cap: int | None = None,
) -> tuple[int, int]:
    """Return (hp_dam, total_damage) using ROM breath formulas."""

    caster_hit = int(getattr(caster, "hit", 0) or 0)
    hpch = max(min_hp, caster_hit)

    low = c_div(hpch, low_divisor) + 1
    if high_cap is not None:
        high = high_cap
    else:
        high = c_div(hpch, high_divisor)
    if high < low:
        high = low

    hp_dam = rng_mm.number_range(low, high)
    dice_dam = rng_mm.dice(level, dice_size)
    dam = max(hp_dam + c_div(dice_dam, 10), dice_dam + c_div(hp_dam, 10))
    return hp_dam, dam


def acid_blast(caster: Character, target: Character | None = None) -> int:
    """ROM spell_acid_blast: dice(level, 12) with save-for-half."""
    if target is None:
        raise ValueError("acid_blast requires a target")

    level = max(getattr(caster, "level", 0), 0)
    damage = rng_mm.dice(level, 12)
    if saves_spell(level, target, DamageType.ACID):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def acid_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_acid_breath with save-for-half and acid effects."""

    if caster is None or target is None:
        raise ValueError("acid_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=12,
        low_divisor=11,
        high_divisor=6,
        dice_size=16,
    )

    if saves_spell(level, target, DamageType.ACID):
        acid_effect(target, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
        damage = c_div(dam, 2)
    else:
        acid_effect(target, level, dam, SpellTarget.CHAR)
        damage = dam

    target.hit -= damage
    update_pos(target)
    return damage


def armor(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_armor: apply -20 AC affect with 24 tick duration."""
    target = target or caster
    if target is None:
        raise ValueError("armor requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(name="armor", duration=24, level=level, ac_mod=-20)
    return target.apply_spell_effect(effect)


def axe(caster, target=None):
    """Stub implementation for axe.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def backstab(
    caster: Character,
    target: Character | None = None,
) -> str:
    """Perform a ROM-style backstab using the core attack pipeline."""

    if caster is None or target is None:
        raise ValueError("backstab requires a caster and target")

    weapon = get_wielded_weapon(caster)
    if weapon is None:
        raise ValueError("backstab requires a wielded weapon")

    # Delegate to the shared attack pipeline so THAC0/defense logic applies.
    return attack_round(caster, target, dt="backstab")


def bash(
    caster: Character,
    target: Character | None = None,
    *,
    success: bool | None = None,
    chance: int | None = None,
) -> str:
    """Replicate ROM bash knockdown and damage spread."""

    if caster is None or target is None:
        raise ValueError("bash requires both caster and target")

    bash_type = int(DamageType.BASH)
    if not success:
        return apply_damage(caster, target, 0, bash_type, dt="bash")

    chance = int(chance or 0)
    size = max(0, int(getattr(caster, "size", 0) or 0))
    upper = 2 + 2 * size + c_div(chance, 20)
    damage = rng_mm.number_range(2, max(2, upper))

    # DAZE_STATE in ROM applies 3 * PULSE_VIOLENCE to the victim.
    from mud.config import get_pulse_violence

    victim_daze = 3 * get_pulse_violence()
    target.daze = max(int(getattr(target, "daze", 0) or 0), victim_daze)
    result = apply_damage(caster, target, damage, bash_type, dt="bash")
    target.position = Position.RESTING
    return result


def berserk(
    caster: Character,
    target: Character | None = None,
    *,
    duration: int | None = None,
) -> bool:
    """Apply ROM-style berserk affect bonuses."""

    if caster is None:
        raise ValueError("berserk requires a caster")

    level = max(1, int(getattr(caster, "level", 1) or 1))
    hit_mod = max(1, c_div(level, 5))
    ac_penalty = max(10, 10 * c_div(level, 5))

    if duration is None:
        base = max(1, c_div(level, 8))
        duration = rng_mm.number_fuzzy(base)

    effect = SpellEffect(
        name="berserk",
        duration=duration,
        level=level,
        ac_mod=ac_penalty,
        hitroll_mod=hit_mod,
        damroll_mod=hit_mod,
        affect_flag=AffectFlag.BERSERK,
    )
    return caster.apply_spell_effect(effect)


def bless(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_bless for characters: +hitroll, -saving_throw."""
    target = target or caster
    if target is None:
        raise ValueError("bless requires a target")

    if target.position == Position.FIGHTING:
        return False

    level = max(getattr(caster, "level", 0), 0)
    modifier = c_div(level, 8)
    effect = SpellEffect(
        name="bless",
        duration=6 + level,
        level=level,
        hitroll_mod=modifier,
        saving_throw_mod=-modifier,
    )
    return target.apply_spell_effect(effect)


def blindness(caster: Character, target: Character | None = None) -> bool:
    """Apply ROM ``spell_blindness`` affect and messaging."""

    if caster is None or target is None:
        raise ValueError("blindness requires a target")

    if target.has_affect(AffectFlag.BLIND) or target.has_spell_effect("blindness"):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if saves_spell(level, target, int(DamageType.OTHER)):
        return False

    effect = SpellEffect(
        name="blindness",
        duration=1 + level,
        level=level,
        hitroll_mod=-4,
        affect_flag=AffectFlag.BLIND,
        wear_off_message="You can see again.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are blinded!")

    room = getattr(target, "room", None)
    if room is not None:
        if target.name:
            room_message = f"{target.name} appears to be blinded."
        else:
            room_message = "Someone appears to be blinded."
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_message)

    return True


def burning_hands(caster: Character, target: Character | None = None) -> int:
    """ROM spell_burning_hands damage table with save-for-half."""
    if target is None:
        raise ValueError("burning_hands requires a target")

    dam_each = [
        0,
        0,
        0,
        0,
        0,
        14,
        17,
        20,
        23,
        26,
        29,
        29,
        29,
        30,
        30,
        31,
        31,
        32,
        32,
        33,
        33,
        34,
        34,
        35,
        35,
        36,
        36,
        37,
        37,
        38,
        38,
        39,
        39,
        40,
        40,
        41,
        41,
        42,
        42,
        43,
        43,
        44,
        44,
        45,
        45,
        46,
        46,
        47,
        47,
        48,
        48,
    ]

    level = max(getattr(caster, "level", 0), 0)
    capped_level = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped_level]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    if saves_spell(level, target, DamageType.FIRE):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def call_lightning(caster: Character, target: Character | None = None) -> int:
    """ROM spell_call_lightning: dice(level/2, 8) with save-for-half."""
    if target is None:
        raise ValueError("call_lightning requires a target")

    if not _is_outside(caster):
        _send_to_char(caster, "You must be out of doors.")
        return 0

    if weather.sky < SkyState.RAINING:
        _send_to_char(caster, "You need bad weather.")
        return 0

    caster_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if caster_room is None or target_room is None or caster_room is not target_room:
        return 0

    level = max(getattr(caster, "level", 0), 0)
    dice_level = max(0, c_div(level, 2))
    damage = rng_mm.dice(dice_level, 8)

    if damage <= 0:
        return 0

    _send_to_char(caster, "Mota's lightning strikes your foes!")
    caster_room.broadcast("$n calls Mota's lightning to strike $s foes!", exclude=caster)

    if saves_spell(level, target, DamageType.LIGHTNING):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def calm(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> bool:  # noqa: ARG001 - parity signature
    """Pacify ongoing fights following ROM ``spell_calm``."""

    if caster is None:
        raise ValueError("calm requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return False

    occupants = list(getattr(room, "people", []) or [])
    if not occupants:
        return False

    def _position(character: Character) -> Position:
        try:
            return Position(getattr(character, "position", Position.STANDING))
        except (TypeError, ValueError):  # pragma: no cover - invalid position defaults
            return Position.STANDING

    mlevel = 0
    count = 0
    high_level = 0
    for occupant in occupants:
        if _position(occupant) == Position.FIGHTING:
            count += 1
            level = max(int(getattr(occupant, "level", 0) or 0), 0)
            if getattr(occupant, "is_npc", True):
                mlevel += level
            else:
                mlevel += c_div(level, 2)
            high_level = max(high_level, level)

    caster_level = max(int(getattr(caster, "level", 0) or 0), 0)
    spell_level = override_level if override_level is not None else caster_level
    spell_level = max(spell_level, 0)
    chance = 4 * spell_level - high_level + 2 * count
    if getattr(caster, "is_immortal", None) and caster.is_immortal():
        mlevel = 0

    if rng_mm.number_range(0, chance) < mlevel:
        return False

    for occupant in occupants:
        if getattr(occupant, "is_npc", True):
            imm_flags = int(getattr(occupant, "imm_flags", 0) or 0)
            act_flags = int(getattr(occupant, "act", 0) or 0)
            if imm_flags & int(ImmFlag.MAGIC) or act_flags & int(ActFlag.UNDEAD):
                return False
        if getattr(occupant, "has_affect", None):
            if occupant.has_affect(AffectFlag.CALM) or occupant.has_affect(AffectFlag.BERSERK):
                return False
        if getattr(occupant, "has_spell_effect", None) and occupant.has_spell_effect("frenzy"):
            return False

    duration = max(0, c_div(spell_level, 4))
    applied = False
    for occupant in occupants:
        _send_to_char(occupant, "A wave of calm passes over you.")
        fighting_target = getattr(occupant, "fighting", None)
        if fighting_target is not None or _position(occupant) == Position.FIGHTING:
            stop_fighting(occupant, both=False)
        penalty = -5 if not getattr(occupant, "is_npc", True) else -2
        effect = SpellEffect(
            name="calm",
            duration=duration,
            level=spell_level,
            hitroll_mod=penalty,
            damroll_mod=penalty,
            affect_flag=AffectFlag.CALM,
        )
        occupant.apply_spell_effect(effect)
        applied = True

    return applied


def cause_critical(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_cause_critical`` damage (3d8 + level - 6)."""

    if caster is None or target is None:
        raise ValueError("cause_critical requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    base_damage = rng_mm.dice(3, 8) + level - 6
    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(
        caster,
        target,
        max(0, base_damage),
        DamageType.HARM,
        dt=_CAUSE_SPELL_ATTACK_NOUN,
    )
    return max(0, before - int(getattr(target, "hit", 0) or 0))


def cause_light(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_cause_light`` damage (1d8 + level/3)."""

    if caster is None or target is None:
        raise ValueError("cause_light requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    base_damage = rng_mm.dice(1, 8) + c_div(level, 3)
    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(
        caster,
        target,
        max(0, base_damage),
        DamageType.HARM,
        dt=_CAUSE_SPELL_ATTACK_NOUN,
    )
    return max(0, before - int(getattr(target, "hit", 0) or 0))


def cause_serious(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_cause_serious`` damage (2d8 + level/2)."""

    if caster is None or target is None:
        raise ValueError("cause_serious requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    base_damage = rng_mm.dice(2, 8) + c_div(level, 2)
    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(
        caster,
        target,
        max(0, base_damage),
        DamageType.HARM,
        dt=_CAUSE_SPELL_ATTACK_NOUN,
    )
    return max(0, before - int(getattr(target, "hit", 0) or 0))


def chain_lightning(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_chain_lightning`` bouncing lightning damage."""

    if caster is None or target is None:
        raise ValueError("chain_lightning requires a caster and target")

    room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if room is None or target_room is None or target_room is not room:
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if level <= 0:
        return False

    caster_name = _character_name(caster)
    victim_name = _character_name(target)

    broadcast_room(
        room,
        f"A lightning bolt leaps from {caster_name}'s hand and arcs to {victim_name}.",
        exclude=caster,
    )
    _send_to_char(
        caster,
        f"A lightning bolt leaps from your hand and arcs to {victim_name}.",
    )
    _send_to_char(
        target,
        f"A lightning bolt leaps from {caster_name}'s hand and hits you!",
    )

    damage = rng_mm.dice(level, 6)
    if saves_spell(level, target, DamageType.LIGHTNING):
        damage = c_div(damage, 3)
    apply_damage(caster, target, damage, DamageType.LIGHTNING, dt="chain lightning")

    any_hit = damage > 0
    last_victim: Character = target
    level -= 4

    while level > 0:
        found = False
        occupants = list(getattr(room, "people", []) or [])
        for occupant in occupants:
            if occupant is None or occupant is last_victim:
                continue
            if _is_safe_spell(caster, occupant, area=True):
                continue

            found = True
            last_victim = occupant
            victim_name = _character_name(occupant)
            broadcast_room(
                room,
                f"The bolt arcs to {victim_name}!",
                exclude=occupant,
            )
            _send_to_char(occupant, "The bolt hits you!")

            damage = rng_mm.dice(level, 6)
            if saves_spell(level, occupant, DamageType.LIGHTNING):
                damage = c_div(damage, 3)
            apply_damage(caster, occupant, damage, DamageType.LIGHTNING, dt="chain lightning")
            any_hit = any_hit or damage > 0

            level -= 4
            if level <= 0:
                break

        if found or level <= 0:
            continue

        if last_victim is caster:
            broadcast_room(
                room,
                "The bolt seems to have fizzled out.",
                exclude=caster,
            )
            _send_to_char(caster, "The bolt grounds out through your body.")
            break

        last_victim = caster
        broadcast_room(
            room,
            f"The bolt arcs to {caster_name}...whoops!",
            exclude=caster,
        )
        _send_to_char(caster, "You are struck by your own lightning!")
        damage = rng_mm.dice(level, 6)
        if saves_spell(level, caster, DamageType.LIGHTNING):
            damage = c_div(damage, 3)
        apply_damage(caster, caster, damage, DamageType.LIGHTNING, dt="chain lightning")
        any_hit = any_hit or damage > 0
        level -= 4

    return any_hit


def change_sex(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_change_sex`` affect that randomizes the victim's sex."""

    if caster is None or target is None:
        raise ValueError("change_sex requires a target")

    if target.has_spell_effect("change sex"):
        if target is caster:
            _send_to_char(caster, "You've already been changed.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} has already had their sex changed.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if saves_spell(level, target, DamageType.OTHER):
        return False

    try:
        current_sex = int(getattr(target, "sex", 0) or 0)
    except (TypeError, ValueError):
        current_sex = 0

    new_sex = current_sex
    attempts = 0
    while new_sex == current_sex and attempts < 10:
        new_sex = max(0, min(rng_mm.number_range(0, 2), 2))
        attempts += 1
    if new_sex == current_sex:
        new_sex = (current_sex + 1) % 3

    modifier = new_sex - current_sex
    effect = SpellEffect(name="change sex", duration=2 * level, level=level, sex_delta=modifier)
    target.apply_spell_effect(effect)

    _send_to_char(target, "You feel different.")
    room = getattr(target, "room", None)
    if room is not None:
        victim_name = _character_name(target)
        reflexive = _reflexive_pronoun(target)
        broadcast_room(room, f"{victim_name} doesn't look like {reflexive} anymore...", exclude=target)

    return True


def charm_person(caster: Character, target: Character | None = None) -> bool:
    """Apply ROM ``spell_charm_person`` safeguards and charm affect."""

    if caster is None or target is None:
        raise ValueError("charm_person requires a target")

    if target is caster:
        if hasattr(caster, "messages") and isinstance(caster.messages, list):
            caster.messages.append("You like yourself even better!")
        return False

    if target.has_affect(AffectFlag.CHARM) or target.has_spell_effect("charm person"):
        return False

    if caster.has_affect(AffectFlag.CHARM):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    victim_level = max(int(getattr(target, "level", 0) or 0), 0)
    if level < victim_level:
        return False

    imm_flags = int(getattr(target, "imm_flags", 0) or 0)
    if imm_flags & int(ImmFlag.CHARM):
        return False

    room = getattr(target, "room", None)
    if room is not None:
        flags = int(getattr(room, "room_flags", 0) or 0)
        if flags & int(RoomFlag.ROOM_LAW):
            if hasattr(caster, "messages") and isinstance(caster.messages, list):
                caster.messages.append(
                    "The mayor does not allow charming in the city limits."
                )
            return False

    if saves_spell(level, target, DamageType.CHARM):
        return False

    if getattr(target, "master", None) is not None:
        stop_follower(target)

    add_follower(target, caster)
    target.leader = caster

    base_duration = max(1, c_div(level, 4))
    duration = rng_mm.number_fuzzy(base_duration)

    effect = SpellEffect(
        name="charm person",
        duration=duration,
        level=level,
        affect_flag=AffectFlag.CHARM,
        wear_off_message="You feel more self-confident.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        stop_follower(target)
        return False

    actor_name = getattr(caster, "name", None) or "Someone"
    target_messages = getattr(target, "messages", None)
    if isinstance(target_messages, list):
        target_messages.append(f"Isn't {actor_name} just so nice?")

    if caster is not target:
        target_name = getattr(target, "name", None) or "Someone"
        caster_messages = getattr(caster, "messages", None)
        if isinstance(caster_messages, list):
            caster_messages.append(f"{target_name} looks at you with adoring eyes.")

    return True


def chill_touch(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_chill_touch`` cold damage plus strength debuff."""

    if caster is None or target is None:
        raise ValueError("chill_touch requires a target")

    dam_each = [
        0,
        0,
        0,
        6,
        7,
        8,
        9,
        12,
        13,
        13,
        13,
        14,
        14,
        14,
        15,
        15,
        15,
        16,
        16,
        16,
        17,
        17,
        17,
        18,
        18,
        18,
        19,
        19,
        19,
        20,
        20,
        20,
        21,
        21,
        21,
        22,
        22,
        22,
        23,
        23,
        23,
        24,
        24,
        24,
        25,
        25,
        25,
        26,
        26,
        26,
        27,
    ]

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    capped = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    if saves_spell(capped, target, DamageType.COLD):
        damage = c_div(damage, 2)
    else:
        room = getattr(target, "room", None)
        if room is not None:
            target_name = getattr(target, "name", None) or "Someone"
            message = f"{target_name} turns blue and shivers."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is target:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)

        effect = SpellEffect(
            name="chill touch",
            duration=6,
            level=capped,
            stat_modifiers={Stat.STR: -1},
        )
        target.apply_spell_effect(effect)

    target.hit -= damage
    update_pos(target)
    return damage


def colour_spray(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_colour_spray`` damage with blindness on failed save."""

    if caster is None or target is None:
        raise ValueError("colour_spray requires a target")

    dam_each = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        30,
        35,
        40,
        45,
        50,
        55,
        55,
        55,
        56,
        57,
        58,
        58,
        59,
        60,
        61,
        61,
        62,
        63,
        64,
        64,
        65,
        66,
        67,
        67,
        68,
        69,
        70,
        70,
        71,
        72,
        73,
        73,
        74,
        75,
        76,
        76,
        77,
        78,
        79,
        79,
    ]

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    capped = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped]
    damage = rng_mm.number_range(c_div(base, 2), base * 2)

    caster_name = getattr(caster, "name", None) or "Someone"
    target_name = getattr(target, "name", None) or "Someone"
    caster_msg = (
        f"{{3You spray {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"
    )
    target_msg = (
        f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light across your vision!{{x"
    )
    room_msg = (
        f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"
    )

    if hasattr(caster, "messages"):
        caster.messages.append(caster_msg)
    if hasattr(target, "messages"):
        target.messages.append(target_msg)

    room = getattr(caster, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is caster or occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_msg)

    if saves_spell(capped, target, DamageType.LIGHT):
        damage = c_div(damage, 2)
    else:
        blind_level = c_div(capped, 2)
        original_level = getattr(caster, "level", 0)
        setattr(caster, "level", blind_level)
        try:
            blindness(caster, target)
        finally:
            setattr(caster, "level", original_level)

    target.hit -= damage
    update_pos(target)
    return damage


def continual_light(
    caster: Character,
    target: Object | ObjectData | None = None,
) -> Object | bool | None:
    """ROM ``spell_continual_light`` glow toggle and light ball conjuration."""

    if caster is None:
        raise ValueError("continual_light requires a caster")

    if target is not None:
        if not isinstance(target, (Object, ObjectData)):
            raise TypeError("continual_light target must be an Object or ObjectData")

        extra_flags = _coerce_int(getattr(target, "extra_flags", 0))
        if extra_flags & int(ExtraFlag.GLOW):
            _send_to_char(caster, f"{_object_short_descr(target)} is already glowing.")
            return False

        setattr(target, "extra_flags", extra_flags | int(ExtraFlag.GLOW))
        message = f"{_object_short_descr(target)} glows with a white light."
        _send_to_char(caster, message)

        room = getattr(caster, "room", None)
        if room is not None:
            room.broadcast(message, exclude=caster)
        return True

    room = getattr(caster, "room", None)
    if room is None:
        return None

    light = spawn_object(OBJ_VNUM_LIGHT_BALL)
    if light is None:
        raise ValueError("OBJ_VNUM_LIGHT_BALL prototype is required for continual_light")

    room.add_object(light)

    short_descr = _object_short_descr(light)
    poss = _possessive_pronoun(caster)
    caster_name = _character_name(caster)

    room_message = f"{caster_name} twiddles {poss} thumbs and {short_descr} appears."
    room.broadcast(room_message, exclude=caster)
    _send_to_char(caster, f"You twiddle your thumbs and {short_descr} appears.")
    return light


def control_weather(caster: Character, target: str | None = None) -> bool:
    """ROM ``spell_control_weather`` better/worse barometer adjustments."""

    if caster is None:
        raise ValueError("control_weather requires a caster")

    argument = ""
    if isinstance(target, str):
        argument = target.strip().lower()

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    dice_count = max(0, c_div(level, 3))

    if argument == "better":
        weather.change += rng_mm.dice(dice_count, 4)
    elif argument == "worse":
        weather.change -= rng_mm.dice(dice_count, 4)
    else:
        _send_to_char(caster, "Do you want it to get better or worse?")

    _send_to_char(caster, "Ok.")
    return True


def create_food(caster: Character, target: Object | None = None) -> Object | None:
    """ROM ``spell_create_food`` conjures a mushroom object in the room."""

    if caster is None:
        raise ValueError("create_food requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return None

    mushroom = spawn_object(OBJ_VNUM_MUSHROOM)
    if mushroom is None:
        return None

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    values = _normalize_value_list(mushroom, minimum=2)
    values[0] = c_div(level, 2)
    values[1] = level
    mushroom.value = values

    room.add_object(mushroom)
    message = f"{_object_short_descr(mushroom)} suddenly appears."
    room.broadcast(message, exclude=caster)
    _send_to_char(caster, message)
    return mushroom


def create_rose(caster: Character, target=None) -> Object | None:  # noqa: ARG001 - parity signature
    """ROM ``spell_create_rose`` conjuration that gifts the caster a rose."""

    if caster is None:
        raise ValueError("create_rose requires a caster")

    rose = spawn_object(OBJ_VNUM_ROSE)
    if rose is None:
        raise ValueError("OBJ_VNUM_ROSE prototype is required for create_rose")

    caster.add_object(rose)

    _send_to_char(caster, "You create a beautiful red rose.")
    room = getattr(caster, "room", None)
    if room is not None:
        room.broadcast(f"{_character_name(caster)} has created a beautiful red rose.", exclude=caster)

    return rose


def create_spring(caster: Character, target: Object | None = None) -> Object | None:
    """ROM ``spell_create_spring`` conjures a spring with a level-based timer."""

    if caster is None:
        raise ValueError("create_spring requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return None

    spring = spawn_object(OBJ_VNUM_SPRING)
    if spring is None:
        return None

    spring.timer = max(_coerce_int(getattr(caster, "level", 0)), 0)
    room.add_object(spring)

    message = f"{_object_short_descr(spring)} flows from the ground."
    room.broadcast(message, exclude=caster)
    _send_to_char(caster, message)
    return spring


def create_water(caster: Character, target: Object | None = None) -> bool:
    """ROM ``spell_create_water`` fills drink containers with water."""

    if caster is None or target is None:
        raise ValueError("create_water requires a drink container target")

    raw_item_type = getattr(target, "item_type", None)
    if raw_item_type is None:
        raw_item_type = getattr(getattr(target, "prototype", None), "item_type", None)

    item_type = _resolve_item_type(raw_item_type)
    if item_type is not ItemType.DRINK_CON:
        _send_to_char(caster, "It is unable to hold water.")
        return False

    values = _normalize_value_list(target, minimum=3)
    capacity = max(_coerce_int(values[0]), 0)
    current = max(_coerce_int(values[1]), 0)
    liquid_type = _coerce_int(values[2])

    if liquid_type not in (LIQ_WATER, 0) and current != 0:
        _send_to_char(caster, "It contains some other liquid.")
        return False

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    multiplier = 4 if int(weather.sky) >= int(SkyState.RAINING) else 2
    space_remaining = max(0, capacity - current)
    water = min(level * multiplier, space_remaining)

    if water <= 0:
        _send_to_char(caster, "It is already full of water.")
        return False

    values[2] = LIQ_WATER
    values[1] = current + water
    target.value = values

    message = f"{_object_short_descr(target)} is filled."
    _send_to_char(caster, message)
    room = getattr(caster, "room", None)
    if room is not None:
        room.broadcast(message, exclude=caster)
    return True


def cure_blindness(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM blindness affect with success/failure messaging."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_blindness requires a target")

    if not (
        victim.has_affect(AffectFlag.BLIND)
        or victim.has_spell_effect("blindness")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't blind.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be blinded.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "blindness"):
        _send_to_char(victim, "Your vision returns!")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} is no longer blinded."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_critical(
    caster: Character, target: Character | None = None
) -> int:
    """ROM ``spell_cure_critical`` healing dice and messaging."""

    target = target or caster
    if target is None:
        raise ValueError("cure_critical requires a target")

    level = int(getattr(caster, "level", 0) or 0)
    heal = rng_mm.dice(3, 8) + level - 6

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def cure_disease(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM plague affect with messaging for success/failure."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_disease requires a target")

    if not (
        victim.has_affect(AffectFlag.PLAGUE)
        or victim.has_spell_effect("plague")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't ill.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be diseased.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "plague"):
        _send_to_char(victim, "Your sores vanish.")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} looks relieved as their sores vanish."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_light(caster: Character, target: Character | None = None) -> int:
    """ROM spell_cure_light: heal dice(1,8) + level/3."""
    target = target or caster
    if target is None:
        raise ValueError("cure_light requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    heal = rng_mm.dice(1, 8) + c_div(level, 3)

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def cure_poison(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM poison affect with messaging on outcome."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_poison requires a target")

    if not (
        victim.has_affect(AffectFlag.POISON)
        or victim.has_spell_effect("poison")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't poisoned.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be poisoned.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "poison"):
        _send_to_char(victim, "A warm feeling runs through your body.")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} looks much better."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_serious(
    caster: Character, target: Character | None = None
) -> int:
    """ROM ``spell_cure_serious`` healing dice and messaging."""

    target = target or caster
    if target is None:
        raise ValueError("cure_serious requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    heal = rng_mm.dice(2, 8) + c_div(level, 2)

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def curse(caster, target=None, *, override_level: int | None = None):
    """Port of ROM ``spell_curse`` for characters and objects."""

    if caster is None:
        raise ValueError("curse requires a caster")

    if target is None:
        target = caster

    # Object curse branch mirrors src/magic.c:1725-1778
    if isinstance(target, Object):
        obj = target
        extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        if extra_flags & int(ExtraFlag.NOUNCURSE):
            return False
        if extra_flags & int(ExtraFlag.EVIL):
            _send_to_char(caster, f"{obj.short_descr or 'It'} is already filled with evil.")
            return False

        level = int(getattr(caster, "level", 0) or 0)
        if extra_flags & int(ExtraFlag.BLESS):
            obj_level = int(getattr(obj, "level", getattr(obj.prototype, "level", 0)) or 0)
            if saves_dispel(level, obj_level, duration=0):
                _send_to_char(
                    caster,
                    f"The holy aura of {obj.short_descr or 'it'} is too powerful for you to overcome.",
                )
                return False
            obj.extra_flags = extra_flags & ~int(ExtraFlag.BLESS)
            _send_to_char(caster, f"{obj.short_descr or 'It'} glows with a red aura.")
            extra_flags = int(getattr(obj, "extra_flags", 0) or 0)

        obj.extra_flags = extra_flags | int(ExtraFlag.EVIL)
        _send_to_char(caster, f"{obj.short_descr or 'It'} glows with a malevolent aura.")
        return True

    if not isinstance(target, Character):
        raise TypeError("curse target must be Character or Object")

    victim = target
    if victim.has_affect(AffectFlag.CURSE) or victim.has_spell_effect("curse"):
        return False

    level = override_level if override_level is not None else int(getattr(caster, "level", 0) or 0)
    if saves_spell(level, victim, DamageType.NEGATIVE):
        return False

    modifier = c_div(level, 8)
    duration = 2 * level
    effect = SpellEffect(
        name="curse",
        duration=duration,
        level=level,
        hitroll_mod=-modifier,
        saving_throw_mod=modifier,
        affect_flag=AffectFlag.CURSE,
        wear_off_message="The curse wears off.",
    )
    applied = victim.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(victim, "You feel unclean.")
    if victim is not caster:
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} looks very uncomfortable.")
    return True


def dagger(caster, target=None):
    """Stub implementation for dagger.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def demonfire(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_demonfire`` negative damage plus curse side effects."""

    if caster is None:
        raise ValueError("demonfire requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("demonfire requires a target")

    if not getattr(caster, "is_npc", True) and not is_evil(caster):
        victim = caster
        _send_to_char(caster, "The demons turn upon you!")

    caster.alignment = max(-1000, int(getattr(caster, "alignment", 0) or 0) - 50)

    if victim is not caster:
        room = getattr(caster, "room", None)
        caster_name = getattr(caster, "name", None) or "Someone"
        victim_name = getattr(victim, "name", None) or "Someone"
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                message = f"{caster_name} calls forth the demons of Hell upon {victim_name}!"
                _send_to_char(occupant, message)
        _send_to_char(victim, f"{caster_name} has assailed you with the demons of Hell!")
        _send_to_char(caster, "You conjure forth the demons of hell!")

    level = max(1, int(getattr(caster, "level", 0) or 0))
    damage = rng_mm.dice(level, 10)
    if saves_spell(level, victim, DamageType.NEGATIVE):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)

    curse_level = max(0, c_div(3 * level, 4))
    if (
        curse_level > 0
        and not victim.has_affect(AffectFlag.CURSE)
        and not victim.has_spell_effect("curse")
        and not saves_spell(curse_level, victim, DamageType.NEGATIVE)
    ):
        modifier = c_div(curse_level, 8)
        duration = 2 * curse_level
        effect = SpellEffect(
            name="curse",
            duration=duration,
            level=curse_level,
            hitroll_mod=-modifier,
            saving_throw_mod=modifier,
            affect_flag=AffectFlag.CURSE,
            wear_off_message="The curse wears off.",
        )
        if victim.apply_spell_effect(effect):
            _send_to_char(victim, "You feel unclean.")
            if victim is not caster:
                victim_name = getattr(victim, "name", None) or "Someone"
                _send_to_char(caster, f"{victim_name} looks very uncomfortable.")

    return damage


def detect_evil(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_evil`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_evil requires a target")

    if target.has_affect(AffectFlag.DETECT_EVIL) or target.has_spell_effect("detect evil"):
        if target is caster:
            _send_to_char(caster, "You can already sense evil.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect evil.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect evil",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_EVIL,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_good(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_good`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_good requires a target")

    if target.has_affect(AffectFlag.DETECT_GOOD) or target.has_spell_effect("detect good"):
        if target is caster:
            _send_to_char(caster, "You can already sense good.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect good.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect good",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_GOOD,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_hidden(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_hidden`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_hidden requires a target")

    if target.has_affect(AffectFlag.DETECT_HIDDEN) or target.has_spell_effect("detect hidden"):
        if target is caster:
            _send_to_char(caster, "You are already as alert as you can be.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already sense hidden lifeforms.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect hidden",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_HIDDEN,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your awareness improves.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_invis(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_invis`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_invis requires a target")

    if target.has_affect(AffectFlag.DETECT_INVIS) or target.has_spell_effect("detect invis"):
        if target is caster:
            _send_to_char(caster, "You can already see invisible.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already see invisible things.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect invis",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_INVIS,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_magic(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_magic`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_magic requires a target")

    if target.has_affect(AffectFlag.DETECT_MAGIC) or target.has_spell_effect("detect magic"):
        if target is caster:
            _send_to_char(caster, "You can already sense magical auras.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect magic.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect magic",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_MAGIC,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_poison(caster: Character, target: Object | None = None) -> bool:
    """ROM ``spell_detect_poison`` inspection messaging."""

    if caster is None:
        raise ValueError("detect_poison requires a caster")
    if target is None:
        raise ValueError("detect_poison requires an object target")

    item_type = _resolve_item_type(getattr(target, "item_type", None))
    if item_type is None and hasattr(target, "prototype"):
        item_type = _resolve_item_type(getattr(target.prototype, "item_type", None))

    if item_type in (ItemType.DRINK_CON, ItemType.FOOD):
        values = _normalize_value_list(target, minimum=4)
        if values[3]:
            _send_to_char(caster, "You smell poisonous fumes.")
        else:
            _send_to_char(caster, "It looks delicious.")
    else:
        _send_to_char(caster, "It doesn't look poisoned.")
    return True


def dirt_kicking(caster: Character, target: Character | None = None) -> str:
    """ROM ``do_dirt`` parity: kick dirt to blind an opponent."""

    if caster is None:
        raise ValueError("dirt_kicking requires a caster")

    victim = target or getattr(caster, "fighting", None)
    if victim is None:
        raise ValueError("dirt_kicking requires an opponent")

    if victim is caster:
        _send_to_char(caster, "Very funny.")
        return ""

    if getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.BLIND):
        _send_to_char(caster, f"{_character_name(victim)} is already blinded.")
        return ""
    if getattr(victim, "has_spell_effect", None) and victim.has_spell_effect("dirt kicking"):
        _send_to_char(caster, f"{_character_name(victim)} already has dirt in their eyes.")
        return ""

    chance = _skill_percent(caster, "dirt kicking")
    if chance <= 0:
        _send_to_char(caster, "You get your feet dirty.")
        return ""

    caster_dex = caster.get_curr_stat(Stat.DEX) or 0
    victim_dex = victim.get_curr_stat(Stat.DEX) or 0
    chance += caster_dex
    chance -= 2 * victim_dex

    caster_off = int(getattr(caster, "off_flags", 0) or 0)
    victim_off = int(getattr(victim, "off_flags", 0) or 0)
    caster_haste = getattr(caster, "has_affect", None) and caster.has_affect(AffectFlag.HASTE)
    victim_haste = getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.HASTE)
    if caster_off & int(OffFlag.FAST) or caster_haste:
        chance += 10
    if victim_off & int(OffFlag.FAST) or victim_haste:
        chance -= 25

    caster_level = max(int(getattr(caster, "level", 0) or 0), 0)
    victim_level = max(int(getattr(victim, "level", 0) or 0), 0)
    chance += (caster_level - victim_level) * 2

    room = getattr(caster, "room", None)
    sector = Sector.INSIDE
    if room is not None:
        raw_sector = getattr(room, "sector_type", Sector.INSIDE)
        try:
            sector = Sector(int(raw_sector))
        except (TypeError, ValueError):  # pragma: no cover - defensive fallback
            sector = Sector.INSIDE

    if sector == Sector.INSIDE:
        chance -= 20
    elif sector == Sector.CITY:
        chance -= 10
    elif sector == Sector.FIELD:
        chance += 5
    elif sector == Sector.MOUNTAIN:
        chance -= 10
    elif sector == Sector.DESERT:
        chance += 10
    elif sector in (Sector.WATER_SWIM, Sector.WATER_NOSWIM, Sector.AIR):
        chance = 0

    if chance <= 0:
        _send_to_char(caster, "There isn't any dirt to kick.")
        return ""

    beats = _skill_beats("dirt kicking")
    caster.wait = max(int(getattr(caster, "wait", 0) or 0), beats)

    roll = rng_mm.number_percent()
    if roll < chance:
        victim_name = _character_name(victim)
        caster_name = _character_name(caster)
        if room is not None:
            broadcast_room(
                room,
                f"{victim_name} is blinded by the dirt in their eyes!",
                exclude=victim,
            )
        _send_to_char(victim, f"{caster_name} kicks dirt in your eyes!")
        _send_to_char(victim, "You can't see a thing!")
        _send_to_char(caster, f"You kick dirt in {victim_name}'s eyes!")

        damage = rng_mm.number_range(2, 5)
        result = apply_damage(caster, victim, damage, DamageType.NONE, dt="dirt kicking")

        effect = SpellEffect(
            name="dirt kicking",
            duration=0,
            level=caster_level,
            hitroll_mod=-4,
            affect_flag=AffectFlag.BLIND,
            wear_off_message="You rub the dirt from your eyes.",
        )
        victim.apply_spell_effect(effect)
        check_improve(caster, "dirt kicking", True, 2)
        return result

    check_improve(caster, "dirt kicking", False, 2)
    return apply_damage(caster, victim, 0, DamageType.NONE, dt="dirt kicking")


def disarm(caster: Character, target: Character | None = None) -> bool:
    """ROM ``do_disarm`` parity: strip the victim's wielded weapon."""

    if caster is None:
        raise ValueError("disarm requires a caster")

    victim = target or getattr(caster, "fighting", None)
    if victim is None:
        raise ValueError("disarm requires an opponent")

    victim_weapon = get_wielded_weapon(victim)
    if victim_weapon is None:
        _send_to_char(caster, f"{_character_name(victim)} is not wielding a weapon.")
        return False

    skill = _skill_percent(caster, "disarm")
    if skill <= 0:
        _send_to_char(caster, "You don't know how to disarm opponents.")
        return False

    caster_weapon = get_wielded_weapon(caster)
    hand_to_hand = _skill_percent(caster, "hand to hand")
    caster_off = int(getattr(caster, "off_flags", 0) or 0)

    if caster_weapon is None:
        if hand_to_hand <= 0 and not (caster_off & int(OffFlag.DISARM)):
            _send_to_char(caster, "You must wield a weapon to disarm.")
            return False

    chance = skill
    if caster_weapon is None:
        chance = c_div(chance * max(hand_to_hand, 1), 150)
    else:
        caster_weapon_sn = get_weapon_sn(caster, caster_weapon)
        chance = c_div(chance * get_weapon_skill(caster, caster_weapon_sn), 100)

    victim_weapon_sn = get_weapon_sn(victim, victim_weapon)
    victim_weapon_skill = get_weapon_skill(victim, victim_weapon_sn)
    caster_vs_victim_weapon = get_weapon_skill(caster, victim_weapon_sn)
    chance += c_div(c_div(caster_vs_victim_weapon, 2) - victim_weapon_skill, 2)

    caster_dex = caster.get_curr_stat(Stat.DEX) or 0
    victim_str = victim.get_curr_stat(Stat.STR) or 0
    chance += caster_dex
    chance -= 2 * victim_str

    caster_level = max(int(getattr(caster, "level", 0) or 0), 0)
    victim_level = max(int(getattr(victim, "level", 0) or 0), 0)
    chance += (caster_level - victim_level) * 2
    chance = max(0, chance)

    beats = _skill_beats("disarm")
    caster.wait = max(int(getattr(caster, "wait", 0) or 0), beats)

    roll = rng_mm.number_percent()
    caster_name = _character_name(caster)
    victim_name = _character_name(victim)
    room = getattr(caster, "room", None)

    if roll >= chance:
        _send_to_char(caster, f"You fail to disarm {victim_name}.")
        _send_to_char(victim, f"{caster_name} tries to disarm you, but fails.")
        if room is not None:
            broadcast_room(
                room,
                f"{caster_name} tries to disarm {victim_name}, but fails.",
                exclude=caster,
            )
        check_improve(caster, "disarm", False, 1)
        return False

    extra_flags = int(getattr(victim_weapon, "extra_flags", 0) or 0)
    if extra_flags & int(ExtraFlag.NOREMOVE):
        _send_to_char(caster, f"{victim_name}'s weapon won't budge!")
        _send_to_char(victim, f"{caster_name} tries to disarm you, but your weapon won't budge!")
        if room is not None:
            broadcast_room(
                room,
                f"{caster_name} tries to disarm {victim_name}, but fails.",
                exclude=victim,
            )
        check_improve(caster, "disarm", False, 1)
        return False

    _send_to_char(caster, f"You disarm {victim_name}!")
    _send_to_char(victim, f"{caster_name} disarms you and sends your weapon flying!")
    if room is not None:
        broadcast_room(room, f"{caster_name} disarms {victim_name}!", exclude=caster)

    victim.remove_object(victim_weapon)
    if getattr(victim, "wielded_weapon", None) is victim_weapon:
        victim.wielded_weapon = None
    if hasattr(victim_weapon, "wear_loc"):
        victim_weapon.wear_loc = int(WearLocation.NONE)

    drop_room = getattr(victim, "room", None)
    if drop_room is not None and hasattr(drop_room, "add_object"):
        drop_room.add_object(victim_weapon)
    else:
        victim.add_object(victim_weapon)

    check_improve(caster, "disarm", True, 1)
    return True


def dispel_evil(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_dispel_evil`` holy damage with alignment gating."""

    if caster is None:
        raise ValueError("dispel_evil requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("dispel_evil requires a target")

    if not getattr(caster, "is_npc", True) and is_evil(caster):
        victim = caster

    if is_good(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        room = getattr(caster, "room", None)
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                _send_to_char(occupant, f"Mota protects {victim_name}.")
        _send_to_char(caster, f"Mota protects {victim_name}.")
        return 0

    if is_neutral(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} does not seem to be affected.")
        return 0

    level = max(1, int(getattr(caster, "level", 0) or 0))
    victim_hit = max(0, int(getattr(victim, "hit", 0) or 0))
    if victim_hit > level * 4:
        damage = rng_mm.dice(level, 4)
    else:
        damage = max(victim_hit, rng_mm.dice(level, 4))
    if saves_spell(level, victim, DamageType.HOLY):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)
    return damage


def dispel_good(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_dispel_good`` negative damage with alignment gating."""

    if caster is None:
        raise ValueError("dispel_good requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("dispel_good requires a target")

    if not getattr(caster, "is_npc", True) and is_good(caster):
        victim = caster

    if is_evil(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        room = getattr(caster, "room", None)
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                _send_to_char(occupant, f"{victim_name} is protected by {victim_name}'s evil.")
        _send_to_char(caster, f"{victim_name} is protected by {victim_name}'s evil.")
        return 0

    if is_neutral(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} does not seem to be affected.")
        return 0

    level = max(1, int(getattr(caster, "level", 0) or 0))
    victim_hit = max(0, int(getattr(victim, "hit", 0) or 0))
    if victim_hit > level * 4:
        damage = rng_mm.dice(level, 4)
    else:
        damage = max(victim_hit, rng_mm.dice(level, 4))
    if saves_spell(level, victim, DamageType.NEGATIVE):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)
    return damage


def dispel_magic(caster: Character, target: Character | None = None) -> bool:
    """ROM-style dispel_magic: attempt to strip active spell effects."""

    if caster is None:
        raise ValueError("dispel_magic requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("dispel_magic requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effects = getattr(target, "spell_effects", {})
    if not isinstance(effects, dict) or not effects:
        return False

    success = False
    for effect_name in list(effects.keys()):
        if check_dispel(level, target, effect_name):
            success = True

    return success


def dodge(caster, target=None):
    """Stub implementation for dodge.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def earthquake(caster: Character, target=None) -> bool:  # noqa: ARG001 - parity signature
    """ROM ``spell_earthquake`` area bash damage with flying immunity."""

    if caster is None:
        raise ValueError("earthquake requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return False

    _send_to_char(caster, "The earth trembles beneath your feet!")
    room.broadcast(f"{_character_name(caster)} makes the earth tremble and shiver.", exclude=caster)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    caster_area = getattr(room, "area", None)

    for victim in list(character_registry):
        victim_room = getattr(victim, "room", None)
        if victim_room is None:
            continue

        if victim_room is room:
            if victim is caster or _is_safe_spell(caster, victim, area=True):
                continue

            if getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.FLYING):
                apply_damage(caster, victim, 0, DamageType.BASH, dt="earthquake")
            else:
                damage = level + rng_mm.dice(2, 8)
                apply_damage(caster, victim, damage, DamageType.BASH, dt="earthquake")
            continue

        if caster_area is not None and getattr(victim_room, "area", None) is caster_area:
            _send_to_char(victim, "The earth trembles and shivers.")

    return True


def enchant_armor(caster, target=None):
    """Stub implementation for enchant_armor.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def enchant_weapon(caster, target=None):
    """Stub implementation for enchant_weapon.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def energy_drain(caster, target=None):
    """Stub implementation for energy_drain.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def enhanced_damage(caster, target=None):
    """Stub implementation for enhanced_damage.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def envenom(caster, target=None):
    """Stub implementation for envenom.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def faerie_fire(caster: Character, target: Character | None = None) -> bool:
    """Apply ROM ``spell_faerie_fire`` glow with AC penalty and messaging."""

    if caster is None or target is None:
        raise ValueError("faerie_fire requires a target")

    if target.has_affect(AffectFlag.FAERIE_FIRE) or target.has_spell_effect("faerie fire"):
        if target is caster:
            _send_to_char(caster, "You are already surrounded by a pink outline.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already surrounded by a pink outline.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    duration = level
    ac_penalty = 2 * level

    effect = SpellEffect(
        name="faerie fire",
        duration=duration,
        level=level,
        ac_mod=ac_penalty,
        affect_flag=AffectFlag.FAERIE_FIRE,
        wear_off_message="The pink aura around you fades away.",
    )

    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "You are surrounded by a pink outline.")
    room = getattr(target, "room", None)
    if room is not None:
        broadcast_room(
            room,
            f"{_character_name(target)} is surrounded by a pink outline.",
            exclude=target,
        )

    return True


def faerie_fog(caster: Character, target: Character | None = None) -> bool:
    """Reveal hidden characters per ROM ``spell_faerie_fog`` semantics."""

    if caster is None:
        raise ValueError("faerie_fog requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        _send_to_char(caster, "You conjure a cloud of purple smoke.")
        return False

    broadcast_room(
        room,
        f"{_character_name(caster)} conjures a cloud of purple smoke.",
        exclude=caster,
    )
    _send_to_char(caster, "You conjure a cloud of purple smoke.")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    revealed_any = False

    occupants = list(getattr(room, "people", []) or [])
    for occupant in occupants:
        if occupant is None:
            continue
        if getattr(occupant, "invis_level", 0) > 0:
            continue
        if occupant is caster:
            continue
        if saves_spell(level, occupant, DamageType.OTHER):
            continue

        if hasattr(occupant, "remove_spell_effect"):
            occupant.remove_spell_effect("invis")
            occupant.remove_spell_effect("mass invis")
            occupant.remove_spell_effect("sneak")

        if hasattr(occupant, "remove_affect"):
            occupant.remove_affect(AffectFlag.HIDE)
            occupant.remove_affect(AffectFlag.INVISIBLE)
            occupant.remove_affect(AffectFlag.SNEAK)

        broadcast_room(
            room,
            f"{_character_name(occupant)} is revealed!",
            exclude=occupant,
        )
        _send_to_char(occupant, "You are revealed!")
        revealed_any = True

    return revealed_any


def farsight(caster, target=None):
    """Stub implementation for farsight.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fast_healing(caster, target=None):
    """Stub implementation for fast_healing.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fire_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_fire_breath with room splash damage."""

    if caster is None or target is None:
        raise ValueError("fire_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=10,
        low_divisor=9,
        high_divisor=5,
        dice_size=20,
    )

    room = getattr(target, "room", None) or getattr(caster, "room", None)
    occupants: list[Character] = []
    if room is not None:
        fire_effect(room, level, c_div(dam, 2), SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if person is target:
            if saves_spell(level, person, DamageType.FIRE):
                fire_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)
            else:
                fire_effect(person, level, dam, SpellTarget.CHAR)
                actual = dam
            primary_damage = actual
        else:
            save_level = max(0, level - 2)
            if saves_spell(save_level, person, DamageType.FIRE):
                fire_effect(person, c_div(level, 4), c_div(dam, 8), SpellTarget.CHAR)
                actual = c_div(dam, 4)
            else:
                fire_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)

        person.hit -= actual
        update_pos(person)

    return primary_damage


def fireball(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_fireball`` damage table with save-for-half."""

    if caster is None or target is None:
        raise ValueError("fireball requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    dam_each = (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
        80,
        82,
        84,
        86,
        88,
        90,
        92,
        94,
        96,
        98,
        100,
        102,
        104,
        106,
        108,
        110,
        112,
        114,
        116,
        118,
        120,
        122,
        124,
        126,
        128,
        130,
    )
    index = min(level, len(dam_each) - 1)
    base = dam_each[index]
    low = c_div(base, 2)
    high = base * 2
    roll = rng_mm.number_range(low, high)
    damage = roll
    if saves_spell(level, target, DamageType.FIRE):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(caster, target, max(0, damage), DamageType.FIRE, dt="fireball")
    return max(0, before - int(getattr(target, "hit", 0) or 0))


def fireproof(caster: Character, target: Object | ObjectData | None = None) -> bool:
    """ROM ``spell_fireproof`` object protection."""

    if caster is None or target is None:
        raise ValueError("fireproof requires a caster and object")

    if isinstance(target, ObjectData):
        obj: Object | ObjectData = target
    elif isinstance(target, Object):
        obj = target
    else:
        raise TypeError("fireproof target must be an Object or ObjectData")

    extra_flags = _coerce_int(getattr(obj, "extra_flags", 0))
    if extra_flags & int(ExtraFlag.BURN_PROOF):
        _send_to_char(caster, f"{_object_short_descr(obj)} is already protected from burning.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    duration = rng_mm.number_fuzzy(max(0, c_div(level, 4)))
    affect = Affect(
        where=_TO_OBJECT,
        type=0,
        level=level,
        duration=duration,
        location=_APPLY_NONE,
        modifier=0,
        bitvector=int(ExtraFlag.BURN_PROOF),
    )
    setattr(affect, "spell_name", "fireproof")
    setattr(affect, "wear_off_message", _OBJECT_FIREPROOF_WEAR_OFF)

    affects = getattr(obj, "affected", None)
    if isinstance(affects, list):
        affects.append(affect)
    else:
        setattr(obj, "affected", [affect])

    obj.extra_flags = extra_flags | int(ExtraFlag.BURN_PROOF)

    message = f"{_object_short_descr(obj)} is surrounded by a protective aura."
    _send_to_char(caster, f"You protect {_object_short_descr(obj)} from fire.")

    room = getattr(caster, "room", None)
    if room is not None:
        broadcast_room(room, message, exclude=caster)

    return True


def flail(caster, target=None):
    """Stub implementation for flail.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def flamestrike(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_flamestrike`` holy fire damage."""

    if caster is None or target is None:
        raise ValueError("flamestrike requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    dice_count = 6 + c_div(level, 2)
    damage = rng_mm.dice(dice_count, 8)
    if saves_spell(level, target, DamageType.FIRE):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(caster, target, max(0, damage), DamageType.FIRE, dt="flamestrike")
    return max(0, before - int(getattr(target, "hit", 0) or 0))


def floating_disc(caster: Character, target=None):  # noqa: ARG001 - parity signature
    """Create and equip the ROM floating disc container."""

    if caster is None:
        raise ValueError("floating_disc requires a caster")

    equipment = getattr(caster, "equipment", {}) or {}
    floating_item = None
    if isinstance(equipment, dict):
        floating_item = equipment.get("float") or equipment.get("floating")

    if floating_item is not None:
        flags = int(getattr(floating_item, "extra_flags", 0) or 0)
        if not flags and hasattr(floating_item, "prototype"):
            try:
                flags = int(getattr(floating_item.prototype, "extra_flags", 0) or 0)
            except (TypeError, ValueError):
                flags = 0
        if flags & int(ExtraFlag.NOREMOVE):
            _send_to_char(caster, f"You can't remove {_object_short_descr(floating_item)}.")
            return False
        if isinstance(equipment, dict):
            equipment.pop("float", None)
            equipment.pop("floating", None)
        floating_item.wear_loc = int(WearLocation.NONE)
        if hasattr(caster, "add_object"):
            caster.add_object(floating_item)

    disc = spawn_object(OBJ_VNUM_DISC)
    if disc is None:
        raise ValueError("floating_disc requires OBJ_VNUM_DISC prototype")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    values = _normalize_value_list(disc, minimum=4)
    values[0] = level * 10
    values[3] = level * 5
    disc.value = values

    timer_reduction = rng_mm.number_range(0, c_div(level, 2))
    disc.timer = max(level * 2 - timer_reduction, 0)
    disc.wear_loc = int(WearLocation.FLOAT)

    caster.add_object(disc)
    caster.equip_object(disc, "float")

    room = getattr(caster, "room", None)
    if room is not None:
        broadcast_room(room, f"{_character_name(caster)} has created a floating black disc.", exclude=caster)
    _send_to_char(caster, "You create a floating disc.")

    return disc


def fly(caster, target=None):
    """ROM ``spell_fly`` affect application with duplicate handling."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("fly requires a target")

    already_airborne = False
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.FLYING):
        already_airborne = True
    if getattr(target, "has_spell_effect", None):
        if target.has_spell_effect("fly"):
            already_airborne = True

    if already_airborne:
        if target is caster:
            _send_to_char(caster, "You are already airborne.")
        else:
            name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't need your help to fly.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="fly",
        duration=level + 3,
        level=level,
        affect_flag=AffectFlag.FLYING,
        wear_off_message="You slowly float to the ground.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "Your feet rise off the ground.")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{target.name}'s feet rise off the ground."
            if getattr(target, "name", None)
            else "Someone's feet rise off the ground."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def frenzy(caster: Character, target: Character | None = None) -> bool:  # noqa: ARG001 - parity signature
    """Clerical frenzy buff mirroring ROM ``spell_frenzy``."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("frenzy requires a target")

    already_frenzied = False
    if getattr(target, "has_spell_effect", None):
        if target.has_spell_effect("frenzy"):
            already_frenzied = True
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.BERSERK):
        already_frenzied = True

    if already_frenzied:
        if target is caster:
            _send_to_char(caster, "You are already in a frenzy.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already in a frenzy.")
        return False

    if getattr(target, "has_spell_effect", None) and target.has_spell_effect("calm"):
        if target is caster:
            _send_to_char(caster, "Why don't you just relax for a while?")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} doesn't look like they want to fight anymore.")
        return False

    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.CALM):
        if target is caster:
            _send_to_char(caster, "Why don't you just relax for a while?")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} doesn't look like they want to fight anymore.")
        return False

    caster_good = is_good(caster)
    caster_neutral = is_neutral(caster)
    caster_evil = is_evil(caster)
    target_good = is_good(target)
    target_neutral = is_neutral(target)
    target_evil = is_evil(target)

    if (caster_good and not target_good) or (caster_neutral and not target_neutral) or (caster_evil and not target_evil):
        name = _character_name(target)
        _send_to_char(caster, f"Your god doesn't seem to like {name}")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    duration = c_div(level, 3)
    hit_dam_mod = c_div(level, 6)
    ac_penalty = 10 * c_div(level, 12)

    effect = SpellEffect(
        name="frenzy",
        duration=duration,
        level=level,
        hitroll_mod=hit_dam_mod,
        damroll_mod=hit_dam_mod,
        ac_mod=ac_penalty,
        wear_off_message="Your rage ebbs.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You are filled with holy wrath!")

    room = getattr(target, "room", None)
    if room is not None:
        name = _character_name(target)
        message = f"{name} gets a wild look in their eyes!"
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def frost_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_frost_breath mirroring cold room effects."""

    if caster is None or target is None:
        raise ValueError("frost_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=12,
        low_divisor=11,
        high_divisor=6,
        dice_size=16,
    )

    room = getattr(target, "room", None) or getattr(caster, "room", None)
    occupants: list[Character] = []
    if room is not None:
        cold_effect(room, level, c_div(dam, 2), SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if person is target:
            if saves_spell(level, person, DamageType.COLD):
                cold_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)
            else:
                cold_effect(person, level, dam, SpellTarget.CHAR)
                actual = dam
            primary_damage = actual
        else:
            save_level = max(0, level - 2)
            if saves_spell(save_level, person, DamageType.COLD):
                cold_effect(person, c_div(level, 4), c_div(dam, 8), SpellTarget.CHAR)
                actual = c_div(dam, 4)
            else:
                cold_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)

        person.hit -= actual
        update_pos(person)

    return primary_damage


def gas_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_gas_breath poisoning everyone in the room."""

    if caster is None:
        raise ValueError("gas_breath requires a caster")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=16,
        low_divisor=15,
        high_divisor=15,
        dice_size=12,
        high_cap=8,
    )

    room = getattr(caster, "room", None) or getattr(target, "room", None)
    occupants: list[Character] = []
    if room is not None:
        poison_effect(room, level, dam, SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target is not None and target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if saves_spell(level, person, DamageType.POISON):
            poison_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
            actual = c_div(dam, 2)
        else:
            poison_effect(person, level, dam, SpellTarget.CHAR)
            actual = dam

        person.hit -= actual
        update_pos(person)

        if primary_damage == 0 and ((target is None) or person is target):
            primary_damage = actual

    return primary_damage


def _gate_fail(caster: Character | None) -> bool:
    if caster is not None:
        _send_to_char(caster, "You failed.")
    return False


def gate(caster: Character, target: Character | None = None):
    """Teleport the caster (and pet) to the target's room per ROM ``spell_gate``."""

    if caster is None or target is None:
        raise ValueError("gate requires a target")

    current_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if current_room is None or target_room is None or caster is target:
        return _gate_fail(caster)

    if not can_see_room(caster, target_room):
        return _gate_fail(caster)

    def _room_flags(room) -> int:
        try:
            return int(getattr(room, "room_flags", 0) or 0)
        except (TypeError, ValueError):
            return 0

    target_flags = _room_flags(target_room)
    current_flags = _room_flags(current_room)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    try:
        target_level = int(getattr(target, "level", 0) or 0)
    except (TypeError, ValueError):
        target_level = 0

    if target_flags & int(RoomFlag.ROOM_SAFE):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_PRIVATE):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_SOLITARY):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_NO_RECALL):
        return _gate_fail(caster)
    if current_flags & int(RoomFlag.ROOM_NO_RECALL):
        return _gate_fail(caster)
    if target_level >= level + 3:
        return _gate_fail(caster)
    if is_clan_member(target) and not is_same_clan(caster, target):
        return _gate_fail(caster)

    is_target_npc = bool(getattr(target, "is_npc", True))
    if not is_target_npc and target_level >= LEVEL_HERO:
        return _gate_fail(caster)

    if is_target_npc:
        try:
            imm_flags = int(getattr(target, "imm_flags", 0) or 0)
        except (TypeError, ValueError):
            imm_flags = 0
        if imm_flags & int(ImmFlag.SUMMON):
            return _gate_fail(caster)
        if saves_spell(level, target, DamageType.OTHER):
            return _gate_fail(caster)

    caster_name = _character_name(caster)
    broadcast_room(current_room, f"{caster_name} steps through a gate and vanishes.", exclude=caster)
    _send_to_char(caster, "You step through a gate and vanish.")

    caster.was_in_room = current_room
    current_room.remove_character(caster)
    target_room.add_character(caster)

    broadcast_room(target_room, f"{caster_name} has arrived through a gate.", exclude=caster)
    view = look(caster)
    if view:
        _send_to_char(caster, view)

    pet = getattr(caster, "pet", None)
    if isinstance(pet, Character) and getattr(pet, "room", None) is current_room:
        pet_name = _character_name(pet)
        broadcast_room(current_room, f"{pet_name} steps through a gate and vanishes.", exclude=pet)
        _send_to_char(pet, "You step through a gate and vanish.")

        pet.was_in_room = current_room
        current_room.remove_character(pet)
        target_room.add_character(pet)

        broadcast_room(target_room, f"{pet_name} has arrived through a gate.", exclude=pet)
        pet_view = look(pet)
        if pet_view:
            _send_to_char(pet, pet_view)

    return True


def general_purpose(caster, target=None):
    """Stub implementation for general_purpose.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def giant_strength(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> bool:
    """ROM ``spell_giant_strength`` strength buff with duplicate gating."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("giant_strength requires a target")

    if target.has_spell_effect("giant strength"):
        if target is caster:
            _send_to_char(caster, "You are already as strong as you can get!")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} can't get any stronger.")
        return False

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(int(base_level or 0), 0)
    modifier = 1
    if level >= 18:
        modifier += 1
    if level >= 25:
        modifier += 1
    if level >= 32:
        modifier += 1

    effect = SpellEffect(
        name="giant strength",
        duration=level,
        level=level,
        stat_modifiers={Stat.STR: modifier},
        wear_off_message="You feel weaker.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "Your muscles surge with heightened power!")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{_character_name(target)}'s muscles surge with heightened power."
            if getattr(target, "name", None)
            else "Someone's muscles surge with heightened power."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def haggle(caster, target=None):
    """Stub implementation for haggle.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def hand_to_hand(caster, target=None):
    """Stub implementation for hand_to_hand.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def haste(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> bool:
    """ROM ``spell_haste``: apply AFF_HASTE with slow-dispel support."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("haste requires a target")

    if target.has_spell_effect("haste") or target.has_affect(AffectFlag.HASTE):
        if target is caster:
            _send_to_char(caster, "You can't move any faster!")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already moving as fast as they can.")
        return False

    off_flags = int(getattr(target, "off_flags", 0) or 0)
    if off_flags & int(OffFlag.FAST):
        if target is caster:
            _send_to_char(caster, "You can't move any faster!")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already moving as fast as they can.")
        return False

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(int(base_level or 0), 0)

    if target.has_affect(AffectFlag.SLOW) or target.has_spell_effect("slow"):
        if not check_dispel(level, target, "slow"):
            if target is not caster:
                _send_to_char(caster, "Spell failed.")
            _send_to_char(target, "You feel momentarily faster.")
            return False

        room = getattr(target, "room", None)
        if room is not None:
            message = (
                f"{_character_name(target)} is moving less slowly."
                if getattr(target, "name", None)
                else "Someone is moving less slowly."
            )
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is target:
                    continue
                _send_to_char(occupant, message)
        return True

    modifier = 1
    if level >= 18:
        modifier += 1
    if level >= 25:
        modifier += 1
    if level >= 32:
        modifier += 1

    duration = c_div(level, 2) if target is caster else c_div(level, 4)
    effect = SpellEffect(
        name="haste",
        duration=duration,
        level=level,
        stat_modifiers={Stat.DEX: modifier},
        affect_flag=AffectFlag.HASTE,
        wear_off_message="You feel yourself slow down.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You feel yourself moving more quickly.")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{_character_name(target)} is moving more quickly."
            if getattr(target, "name", None)
            else "Someone is moving more quickly."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    if target is not caster:
        _send_to_char(caster, "Ok.")

    return True


def heal(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_heal`` fixed healing with warm feeling messaging."""

    target = target or caster
    if target is None:
        raise ValueError("heal requires a target")

    heal_amount = 100
    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal_amount, max_hit)
    else:
        target.hit += heal_amount

    update_pos(target)
    _send_to_char(target, "A warm feeling fills your body.")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal_amount


def heat_metal(caster, target=None):
    """Stub implementation for heat_metal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def hide(caster, target=None):
    """Stub implementation for hide.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def high_explosive(caster, target=None):
    """Stub implementation for high_explosive.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def holy_word(caster: Character, target=None):  # noqa: ARG001 - parity signature
    """Mass alignment spell mirroring ROM ``spell_holy_word``."""

    if caster is None:
        raise ValueError("holy_word requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return False

    caster_good = is_good(caster)
    caster_evil = is_evil(caster)
    caster_neutral = is_neutral(caster)
    level = max(int(getattr(caster, "level", 0) or 0), 0)

    caster_name = _character_name(caster)
    broadcast_room(room, f"{caster_name} utters a word of divine power!", exclude=caster)
    _send_to_char(caster, "You utter a word of divine power.")

    any_effect = False

    occupants = list(getattr(room, "people", []) or [])
    energy_damage_type = DamageType.ENERGY

    for victim in occupants:
        if victim is None:
            continue

        victim_good = is_good(victim)
        victim_evil = is_evil(victim)
        victim_neutral = is_neutral(victim)

        if (caster_good and victim_good) or (caster_evil and victim_evil) or (caster_neutral and victim_neutral):
            _send_to_char(victim, "You feel full more powerful.")
            frenzy(caster, victim)
            bless(caster, victim)
            any_effect = True
            continue

        if (caster_good and victim_evil) or (caster_evil and victim_good):
            if not _is_safe_spell(caster, victim, area=True):
                curse(caster, victim)
                _send_to_char(victim, "You are struck down!")
                damage = rng_mm.dice(level, 6)
                apply_damage(
                    caster,
                    victim,
                    damage,
                    energy_damage_type,
                    dt="holy word",
                )
                any_effect = True
            continue

        if caster_neutral and not victim_neutral:
            if not _is_safe_spell(caster, victim, area=True):
                half_level = max(0, c_div(level, 2))
                curse(caster, victim, override_level=half_level)
                _send_to_char(victim, "You are struck down!")
                damage = rng_mm.dice(level, 4)
                apply_damage(
                    caster,
                    victim,
                    damage,
                    energy_damage_type,
                    dt="holy word",
                )
                any_effect = True

    _send_to_char(caster, "You feel drained.")
    caster.move = 0
    caster.hit = c_div(int(getattr(caster, "hit", 0) or 0), 2)
    return any_effect


def identify(caster: Character, target: Object | ObjectData | None = None) -> bool:
    """Appraise an object mirroring ROM ``spell_identify`` output."""

    if caster is None:
        raise ValueError("identify requires a caster")
    if target is None:
        raise ValueError("identify requires an object target")

    obj = target
    proto = getattr(obj, "prototype", None)

    name = getattr(obj, "name", None)
    if not name and proto is not None:
        name = getattr(proto, "name", None)
    short_descr = getattr(obj, "short_descr", None)
    if not name:
        name = short_descr or getattr(proto, "short_descr", None) or "object"

    item_type = _resolve_item_type(getattr(obj, "item_type", None) or getattr(proto, "item_type", None))
    type_name = _item_type_name(item_type)

    extra_flags = _coerce_int(getattr(obj, "extra_flags", 0))
    if not extra_flags and proto is not None:
        extra_flags = _coerce_int(getattr(proto, "extra_flags", 0))

    _send_to_char(caster, f"Object '{name}' is type {type_name}, extra flags {_extra_bit_name(extra_flags)}.")
    _send_to_char(
        caster,
        f"Weight is {_resolve_weight(obj)}, value is {_resolve_cost(obj)}, level is {_resolve_level(obj)}.",
    )

    values = _normalize_value_list(obj, minimum=5)
    resolved_type = item_type

    if resolved_type in (ItemType.SCROLL, ItemType.POTION, ItemType.PILL):
        level = _coerce_int(values[0])
        spell_chunks: list[str] = []
        for raw_index in values[1:5]:
            skill_name = _skill_name_from_value(_coerce_int(raw_index))
            if skill_name:
                spell_chunks.append(f" '{skill_name}'")
        line = f"Level {level} spells of:"
        if spell_chunks:
            line += "".join(spell_chunks)
        line += "."
        _send_to_char(caster, line)
    elif resolved_type in (ItemType.WAND, ItemType.STAFF):
        charges = _coerce_int(values[2])
        level = _coerce_int(values[0])
        spell_name = _skill_name_from_value(_coerce_int(values[3]))
        line = f"Has {charges} charges of level {level}"
        if spell_name:
            line += f" '{spell_name}'"
        line += "."
        _send_to_char(caster, line)
    elif resolved_type == ItemType.DRINK_CON:
        liquid = _lookup_liquid(_coerce_int(values[2]))
        _send_to_char(caster, f"It holds {liquid.color}-colored {liquid.name}.")
    elif resolved_type == ItemType.CONTAINER:
        capacity = _coerce_int(values[0])
        max_weight = _coerce_int(values[3])
        flags = _container_flag_name(_coerce_int(values[1]))
        _send_to_char(caster, f"Capacity: {capacity}#  Maximum weight: {max_weight}#  flags: {flags}")
        weight_multiplier = _coerce_int(values[4])
        if weight_multiplier != 100:
            _send_to_char(caster, f"Weight multiplier: {weight_multiplier}%")
    elif resolved_type == ItemType.WEAPON:
        _send_to_char(caster, f"Weapon type is {_weapon_type_name(_coerce_int(values[0]))}.")
        dice_count = _coerce_int(values[1])
        dice_size = _coerce_int(values[2])
        new_format = bool(getattr(obj, "new_format", False) or (proto and getattr(proto, "new_format", False)))
        if new_format:
            average = c_div((1 + dice_size) * dice_count, 2)
            _send_to_char(caster, f"Damage is {dice_count}d{dice_size} (average {average}).")
        else:
            average = c_div(dice_count + dice_size, 2)
            _send_to_char(caster, f"Damage is {dice_count} to {dice_size} (average {average}).")
        weapon_flags = _weapon_bit_name(_coerce_int(values[4]))
        if weapon_flags != "none":
            _send_to_char(caster, f"Weapons flags: {weapon_flags}")
    elif resolved_type == ItemType.ARMOR:
        pierce = _coerce_int(values[0])
        bash = _coerce_int(values[1])
        slash = _coerce_int(values[2])
        magic = _coerce_int(values[3])
        _send_to_char(
            caster,
            f"Armor class is {pierce} pierce, {bash} bash, {slash} slash, and {magic} vs. magic.",
        )

    _emit_affect_descriptions(caster, obj)
    return True


def infravision(caster: Character, target: Character | None = None) -> bool:
    """Grant infravision affect mirroring ROM ``spell_infravision``."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("infravision requires a target")

    already_active = False
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.INFRARED):
        already_active = True
    if getattr(target, "has_spell_effect", None) and target.has_spell_effect("infravision"):
        already_active = True

    if already_active:
        if target is caster:
            _send_to_char(caster, "You can already see in the dark.")
        else:
            _send_to_char(caster, f"{_character_name(target)} already has infravision.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    duration = 2 * level
    effect = SpellEffect(
        name="infravision",
        duration=duration,
        level=level,
        affect_flag=AffectFlag.INFRARED,
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "Your eyes glow red.")
    room = getattr(target, "room", None)
    if room is not None:
        broadcast_room(room, f"{_character_name(target)}'s eyes glow red.", exclude=target)

    return True


def invis(caster: Character, target: Character | Object | None = None) -> bool:
    """Apply invisibility to objects or characters per ROM ``spell_invis``."""

    if caster is None:
        raise ValueError("invis requires a caster")

    target = target or caster

    if isinstance(target, ObjectData):
        obj = target
    elif isinstance(target, Object):
        obj = target
    else:
        obj = None

    if obj is not None:
        extra_flags = _coerce_int(getattr(obj, "extra_flags", 0))
        if extra_flags & int(ExtraFlag.INVIS):
            _send_to_char(caster, f"{_object_short_descr(obj)} is already invisible.")
            return False

        level = max(int(getattr(caster, "level", 0) or 0), 0)
        affect = Affect(
            where=_TO_OBJECT,
            type=0,
            level=level,
            duration=level + 12,
            location=_APPLY_NONE,
            modifier=0,
            bitvector=int(ExtraFlag.INVIS),
        )
        setattr(affect, "spell_name", "invisibility")
        setattr(affect, "wear_off_message", _OBJECT_INVIS_WEAR_OFF)

        affects = getattr(obj, "affected", None)
        if isinstance(affects, list):
            affects.append(affect)
        else:
            setattr(obj, "affected", [affect])

        obj.extra_flags = extra_flags | int(ExtraFlag.INVIS)
        message = f"{_object_short_descr(obj)} fades out of sight."
        _send_to_char(caster, message)

        caster_room = getattr(caster, "room", None)
        if caster_room is not None:
            broadcast_room(caster_room, message, exclude=caster)
        return True

    if not isinstance(target, Character):
        raise TypeError("invis target must be Character or Object")

    if target.has_affect(AffectFlag.INVISIBLE) or target.has_spell_effect("invis"):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="invis",
        duration=level + 12,
        level=level,
        affect_flag=AffectFlag.INVISIBLE,
        wear_off_message="You fade back into existence.",
    )

    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "You fade out of existence.")
    room = getattr(target, "room", None)
    if room is not None:
        broadcast_room(room, f"{_character_name(target)} fades out of existence.", exclude=target)
    return True


def kick(
    caster: Character,
    target: Character | None = None,
    *,
    success: bool | None = None,
    roll: int | None = None,
) -> str:
    """ROM do_kick: strike the current opponent for level-based damage."""

    if caster is None:
        raise ValueError("kick requires a caster")

    opponent = target or getattr(caster, "fighting", None)
    if opponent is None:
        raise ValueError("kick requires an opponent")

    try:
        raw_chance = getattr(caster, "skills", {}).get("kick", 0)
        chance = max(0, min(100, int(raw_chance)))
    except (TypeError, ValueError):
        chance = 0

    if roll is None:
        roll = rng_mm.number_percent()
    if success is None:
        success = chance > roll

    if success:
        level = max(1, int(getattr(caster, "level", 1) or 1))
        damage = rng_mm.number_range(1, level)
    else:
        damage = 0

    return apply_damage(caster, opponent, damage, DamageType.BASH, dt="kick")


def know_alignment(caster, target=None):
    """Stub implementation for know_alignment.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lightning_bolt(caster, target=None):
    """Stub implementation for lightning_bolt.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lightning_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_lightning_breath with save-for-half."""

    if caster is None or target is None:
        raise ValueError("lightning_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=10,
        low_divisor=9,
        high_divisor=5,
        dice_size=20,
    )

    if saves_spell(level, target, DamageType.LIGHTNING):
        shock_effect(target, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
        damage = c_div(dam, 2)
    else:
        shock_effect(target, level, dam, SpellTarget.CHAR)
        damage = dam

    target.hit -= damage
    update_pos(target)
    return damage


def locate_object(caster, target=None):
    """Stub implementation for locate_object.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lore(caster, target=None):
    """Stub implementation for lore.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mace(caster, target=None):
    """Stub implementation for mace.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def magic_missile(caster, target=None):
    """Stub implementation for magic_missile.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mass_healing(caster, target=None):
    """Stub implementation for mass_healing.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mass_invis(caster: Character, target: Character | None = None) -> bool:
    """Port ROM ``spell_mass_invis`` group invisibility."""

    if caster is None:
        raise ValueError("mass invis requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        _send_to_char(caster, "Ok.")
        return False

    applied = False
    caster_level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect_level = c_div(caster_level, 2)

    for member in list(getattr(room, "people", []) or []):
        if not is_same_group(member, caster):
            continue
        if member.has_affect(AffectFlag.INVISIBLE) or member.has_spell_effect("mass invis"):
            continue

        broadcast_room(
            room,
            f"{_character_name(member)} slowly fades out of existence.",
            exclude=member,
        )
        _send_to_char(member, "You slowly fade out of existence.")

        effect = SpellEffect(
            name="mass invis",
            duration=24,
            level=effect_level,
            affect_flag=AffectFlag.INVISIBLE,
            wear_off_message="You are no longer invisible.",
        )

        if member.apply_spell_effect(effect):
            applied = True

    _send_to_char(caster, "Ok.")
    return applied


def meditation(caster, target=None):
    """Stub implementation for meditation.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def nexus(caster, target=None):
    """Stub implementation for nexus.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def parry(caster, target=None):
    """Stub implementation for parry.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def pass_door(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_pass_door`` affect application with duplicate handling."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("pass_door requires a target")

    already_shifted = False
    if getattr(target, "has_spell_effect", None) and target.has_spell_effect("pass door"):
        already_shifted = True
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.PASS_DOOR):
        already_shifted = True

    if already_shifted:
        if target is caster:
            _send_to_char(caster, "You are already out of phase.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already shifted out of phase.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    base_duration = max(0, c_div(level, 4))
    duration = rng_mm.number_fuzzy(base_duration)
    effect = SpellEffect(
        name="pass door",
        duration=duration,
        level=level,
        affect_flag=AffectFlag.PASS_DOOR,
        wear_off_message="You feel solid again.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You turn translucent.")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{_character_name(target)} turns translucent."
            if getattr(target, "name", None)
            else "Someone turns translucent."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def peek(caster, target=None):
    """Stub implementation for peek.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def pick_lock(caster, target=None):
    """Stub implementation for pick_lock.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def plague(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_plague`` disease affect with undead/save gating."""

    if caster is None or target is None:
        raise ValueError("plague requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    act_flags = _coerce_int(getattr(target, "act", 0))
    is_undead = bool(getattr(target, "is_npc", False) and act_flags & int(ActFlag.UNDEAD))

    if saves_spell(level, target, DamageType.DISEASE) or is_undead:
        if target is caster:
            _send_to_char(caster, "You feel momentarily ill, but it passes.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} seems to be unaffected.")
        return False

    effect = SpellEffect(
        name="plague",
        duration=max(level, 0),
        level=c_div(3 * level, 4),
        stat_modifiers={Stat.STR: -5},
        affect_flag=AffectFlag.PLAGUE,
        wear_off_message="Your sores vanish.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You scream in agony as plague sores erupt from your skin.")
    room = getattr(target, "room", None)
    if room is not None:
        broadcast_room(
            room,
            f"{_character_name(target)} screams in agony as plague sores erupt from their skin.",
            exclude=target,
        )

    return True


def poison(
    caster: Character,
    target: Character | Object | ObjectData | None = None,
) -> bool:
    """ROM ``spell_poison`` for objects and characters."""

    if caster is None or target is None:
        raise ValueError("poison requires a caster and target")

    if isinstance(target, (Object, ObjectData)):
        obj = target
        item_type = _resolve_item_type(getattr(obj, "item_type", None))
        if item_type is None:
            prototype = getattr(obj, "prototype", None) or getattr(obj, "pIndexData", None)
            item_type = _resolve_item_type(getattr(prototype, "item_type", None))

        if item_type in (ItemType.FOOD, ItemType.DRINK_CON):
            base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
            proto = getattr(obj, "prototype", None) or getattr(obj, "pIndexData", None)
            proto_flags = _coerce_int(getattr(proto, "extra_flags", 0)) if proto is not None else 0
            effective_flags = base_flags | proto_flags

            if effective_flags & (int(ExtraFlag.BLESS) | int(ExtraFlag.BURN_PROOF)):
                _send_to_char(caster, f"Your spell fails to corrupt {_object_short_descr(obj)}.")
                return False

            values = _normalize_value_list(obj, minimum=4)
            values[3] = 1
            obj.value = values

            message = f"{_object_short_descr(obj)} is infused with poisonous vapors."
            _send_to_char(caster, message)
            room = getattr(caster, "room", None)
            if room is not None:
                broadcast_room(room, message, exclude=caster)
            return True

        if item_type is ItemType.WEAPON:
            values = _normalize_value_list(obj, minimum=5)
            weapon_flags = _coerce_int(values[4])
            if hasattr(obj, "weapon_flags"):
                weapon_flags |= _coerce_int(getattr(obj, "weapon_flags", 0))

            disallowed = int(WeaponFlag.FLAMING | WeaponFlag.FROST | WeaponFlag.VAMPIRIC | WeaponFlag.SHARP | WeaponFlag.VORPAL | WeaponFlag.SHOCKING)
            if weapon_flags & disallowed:
                _send_to_char(caster, f"You can't seem to envenom {_object_short_descr(obj)}.")
                return False

            base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
            proto = getattr(obj, "prototype", None) or getattr(obj, "pIndexData", None)
            proto_flags = _coerce_int(getattr(proto, "extra_flags", 0)) if proto is not None else 0
            if (base_flags | proto_flags) & (int(ExtraFlag.BLESS) | int(ExtraFlag.BURN_PROOF)):
                _send_to_char(caster, f"You can't seem to envenom {_object_short_descr(obj)}.")
                return False

            if weapon_flags & int(WeaponFlag.POISON):
                _send_to_char(caster, f"{_object_short_descr(obj)} is already envenomed.")
                return False

            level = max(int(getattr(caster, "level", 0) or 0), 0)
            affect = Affect(
                where=_TO_WEAPON,
                type=0,
                level=c_div(level, 2),
                duration=c_div(level, 8),
                location=_APPLY_NONE,
                modifier=0,
                bitvector=int(WeaponFlag.POISON),
            )
            setattr(affect, "spell_name", "poison")
            setattr(affect, "wear_off_message", "The poison on $p dries up.")

            affects = getattr(obj, "affected", None)
            if isinstance(affects, list):
                affects.append(affect)
            else:
                setattr(obj, "affected", [affect])

            new_flags = weapon_flags | int(WeaponFlag.POISON)
            values[4] = new_flags
            obj.value = values
            setattr(obj, "weapon_flags", new_flags)

            message = f"{_object_short_descr(obj)} is coated with deadly venom."
            _send_to_char(caster, message)
            room = getattr(caster, "room", None)
            if room is not None:
                broadcast_room(room, message, exclude=caster)
            return True

        _send_to_char(caster, f"You can't poison {_object_short_descr(obj)}.")
        return False

    if not isinstance(target, Character):
        raise TypeError("poison target must be Character or Object")

    victim = target
    level = max(int(getattr(caster, "level", 0) or 0), 0)

    if saves_spell(level, victim, DamageType.POISON):
        _send_to_char(victim, "You feel momentarily ill, but it passes.")
        room = getattr(victim, "room", None)
        if room is not None:
            broadcast_room(
                room,
                f"{_character_name(victim)} turns slightly green, but it passes.",
                exclude=victim,
            )
        return False

    effect = SpellEffect(
        name="poison",
        duration=level,
        level=level,
        stat_modifiers={Stat.STR: -2},
        affect_flag=AffectFlag.POISON,
        wear_off_message="You feel less sick.",
    )

    applied = victim.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(victim, "You feel very sick.")
    room = getattr(victim, "room", None)
    if room is not None:
        broadcast_room(
            room,
            f"{_character_name(victim)} looks very ill.",
            exclude=victim,
        )
    return True


def polearm(caster, target=None):
    """Stub implementation for polearm.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def portal(caster, target=None):
    """Stub implementation for portal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def protection_evil(caster, target=None):
    """Stub implementation for protection_evil.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def protection_good(caster, target=None):
    """Stub implementation for protection_good.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def ray_of_truth(caster, target=None):
    """Stub implementation for ray_of_truth.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def recall(caster, target=None):
    """Stub implementation for recall.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def recharge(caster, target=None):
    """Stub implementation for recharge.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def refresh(caster, target=None):
    """Stub implementation for refresh.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def remove_curse(caster, target=None):
    """Stub implementation for remove_curse.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def rescue(
    caster: Character,
    target: Character | None = None,
    *,
    opponent: Character | None = None,
) -> str:
    """ROM ``do_rescue`` tank swap.

    Args:
        caster: Character performing the rescue.
        target: Ally being rescued.
        opponent: Target's opponent (defaults to ``target.fighting``).

    Returns:
        Attacker-facing rescue message mirroring ROM colour codes.
    """

    if caster is None or target is None:
        raise ValueError("rescue requires a caster and target")

    foe = opponent or getattr(target, "fighting", None)
    if foe is None:
        raise ValueError("rescue requires an opponent")

    rescuer_name = getattr(caster, "name", "someone") or "someone"
    victim_name = getattr(target, "name", "someone") or "someone"

    char_msg = f"{{5You rescue {victim_name}!{{x"
    vict_msg = f"{{5{rescuer_name} rescues you!{{x"
    room_msg = f"{{5{rescuer_name} rescues {victim_name}!{{x"

    if hasattr(caster, "messages"):
        caster.messages.append(char_msg)
    if hasattr(target, "messages"):
        target.messages.append(vict_msg)

    room = getattr(caster, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is caster or occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_msg)

    stop_fighting(foe, False)
    stop_fighting(target, False)
    set_fighting(caster, foe)
    set_fighting(foe, caster)

    return char_msg


def sanctuary(caster, target=None):
    """ROM ``spell_sanctuary`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("sanctuary requires a target")

    if target.has_affect(AffectFlag.SANCTUARY) or target.has_spell_effect("sanctuary"):
        message = "You are already in sanctuary." if target is caster else f"{target.name} is already in sanctuary."
        if hasattr(caster, "messages"):
            caster.messages.append(message)
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="sanctuary",
        duration=c_div(level, 6),
        level=level,
        affect_flag=AffectFlag.SANCTUARY,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are surrounded by a white aura.")

    room = getattr(target, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(
                    f"{target.name} is surrounded by a white aura."
                    if target.name
                    else "Someone is surrounded by a white aura."
                )

    return True


def scrolls(caster, target=None):
    """Stub implementation for scrolls.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def second_attack(caster, target=None):
    """Stub implementation for second_attack.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def shield(caster, target=None):
    """ROM ``spell_shield`` AC reduction aura."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("shield requires a target")

    if target.has_spell_effect("shield"):
        message = (
            "You are already shielded from harm."
            if target is caster
            else f"{target.name} is already protected by a shield."
        )
        if hasattr(caster, "messages"):
            caster.messages.append(message)
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="shield",
        duration=8 + level,
        level=level,
        ac_mod=-20,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are surrounded by a force shield.")

    room = getattr(target, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(
                    f"{target.name} is surrounded by a force shield."
                    if target.name
                    else "Someone is surrounded by a force shield."
                )

    return True


def shield_block(caster, target=None):
    """Stub implementation for shield_block.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def shocking_grasp(caster, target=None):
    """Stub implementation for shocking_grasp.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def sleep(caster, target=None):
    """Stub implementation for sleep.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def slow(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> bool:
    """ROM ``spell_slow``: apply AFF_SLOW with haste-dispel support."""

    if caster is None or target is None:
        raise ValueError("slow requires a caster and target")

    if target.has_spell_effect("slow") or target.has_affect(AffectFlag.SLOW):
        if target is caster:
            _send_to_char(caster, "You can't move any slower!")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} can't get any slower than that.")
        return False

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(int(base_level or 0), 0)

    imm_flags = int(getattr(target, "imm_flags", 0) or 0)
    if saves_spell(level, target, DamageType.OTHER) or imm_flags & int(ImmFlag.MAGIC):
        if target is not caster:
            _send_to_char(caster, "Nothing seemed to happen.")
        _send_to_char(target, "You feel momentarily lethargic.")
        return False

    if target.has_affect(AffectFlag.HASTE) or target.has_spell_effect("haste"):
        if not check_dispel(level, target, "haste"):
            if target is not caster:
                _send_to_char(caster, "Spell failed.")
            _send_to_char(target, "You feel momentarily slower.")
            return False

        room = getattr(target, "room", None)
        if room is not None:
            message = (
                f"{_character_name(target)} is moving less quickly."
                if getattr(target, "name", None)
                else "Someone is moving less quickly."
            )
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is target:
                    continue
                _send_to_char(occupant, message)
        return True

    modifier = -1
    if level >= 18:
        modifier -= 1
    if level >= 25:
        modifier -= 1
    if level >= 32:
        modifier -= 1

    duration = c_div(level, 2)
    effect = SpellEffect(
        name="slow",
        duration=duration,
        level=level,
        stat_modifiers={Stat.DEX: modifier},
        affect_flag=AffectFlag.SLOW,
        wear_off_message="You feel yourself speed up.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You feel yourself slowing d o w n...")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{_character_name(target)} starts to move in slow motion."
            if getattr(target, "name", None)
            else "Someone starts to move in slow motion."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def sneak(caster: Character, target: Character | None = None) -> bool:  # noqa: ARG001 - parity signature
    """ROM ``do_sneak``: attempt to apply AFF_SNEAK with skill training."""

    if caster is None:
        raise ValueError("sneak requires a caster")

    _send_to_char(caster, "You attempt to move silently.")

    if hasattr(caster, "remove_spell_effect"):
        caster.remove_spell_effect("sneak")

    if caster.has_affect(AffectFlag.SNEAK):
        return False

    chance = _skill_percent(caster, "sneak")
    roll = rng_mm.number_percent()

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    success = roll < chance

    if success:
        effect = SpellEffect(
            name="sneak",
            duration=level,
            level=level,
            affect_flag=AffectFlag.SNEAK,
        )
        applied = caster.apply_spell_effect(effect) if hasattr(caster, "apply_spell_effect") else False
        if not applied:
            return False
        check_improve(caster, "sneak", True, 3)
        return True

    check_improve(caster, "sneak", False, 3)
    return False


def spear(caster, target=None):
    """Stub implementation for spear.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def staves(caster, target=None):
    """Stub implementation for staves.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def steal(caster, target=None):
    """Stub implementation for steal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def stone_skin(caster: Character, target: Character | None = None) -> bool:  # noqa: ARG001 - parity signature
    """ROM ``spell_stone_skin``: apply a -40 AC buff with duplicate gating."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("stone_skin requires a target")

    if target.has_spell_effect("stone skin"):
        if target is caster:
            _send_to_char(caster, "Your skin is already as hard as a rock.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already as hard as can be.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(name="stone skin", duration=level, level=level, ac_mod=-40)

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "Your skin turns to stone.")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{_character_name(target)}'s skin turns to stone."
            if getattr(target, "name", None)
            else "Someone's skin turns to stone."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def summon(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_summon``: pull a target into the caster's room."""

    if caster is None or target is None:
        raise ValueError("summon requires a target")
    if not isinstance(target, Character):
        raise TypeError("summon target must be a Character")

    if target is caster:
        _send_to_char(caster, "You failed.")
        return False

    caster_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if caster_room is None or target_room is None:
        _send_to_char(caster, "You failed.")
        return False

    if _get_room_flags(caster_room) & int(RoomFlag.ROOM_SAFE):
        _send_to_char(caster, "You failed.")
        return False

    target_flags = _get_room_flags(target_room)
    disallowed = int(RoomFlag.ROOM_SAFE) | int(RoomFlag.ROOM_PRIVATE) | int(RoomFlag.ROOM_SOLITARY) | int(RoomFlag.ROOM_NO_RECALL)
    if target_flags & disallowed:
        _send_to_char(caster, "You failed.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    target_level = max(int(getattr(target, "level", 0) or 0), 0)
    if target_level >= level + 3:
        _send_to_char(caster, "You failed.")
        return False

    if not getattr(target, "is_npc", True) and target_level >= LEVEL_IMMORTAL:
        _send_to_char(caster, "You failed.")
        return False

    if getattr(target, "fighting", None) is not None:
        _send_to_char(caster, "You failed.")
        return False

    act_flags = int(getattr(target, "act", 0) or 0)

    if getattr(target, "is_npc", True):
        if act_flags & int(ActFlag.AGGRESSIVE):
            _send_to_char(caster, "You failed.")
            return False

        imm_flags = int(getattr(target, "imm_flags", 0) or 0)
        if imm_flags & int(ImmFlag.SUMMON):
            _send_to_char(caster, "You failed.")
            return False

        shop = (
            getattr(target, "pShop", None)
            or getattr(getattr(target, "prototype", None), "pShop", None)
            or getattr(getattr(target, "pIndexData", None), "pShop", None)
        )
        if shop is not None:
            _send_to_char(caster, "You failed.")
            return False

        if saves_spell(level, target, DamageType.OTHER):
            _send_to_char(caster, "You failed.")
            return False
    else:
        if act_flags & int(PlayerFlag.NOSUMMON):
            _send_to_char(caster, "You failed.")
            return False

    victim_name = _character_name(target)

    broadcast_room(target_room, f"{victim_name} disappears suddenly.", exclude=target)
    target_room.remove_character(target)
    caster_room.add_character(target)
    broadcast_room(caster_room, f"{victim_name} arrives suddenly.", exclude=target)

    caster_name = _character_name(caster)
    _send_to_char(target, f"{caster_name} has summoned you!")

    view = look(target)
    if view:
        _send_to_char(target, view)

    return True


def sword(caster, target=None):
    """Stub implementation for sword.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def teleport(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_teleport``: send a character to a random room."""

    if caster is None:
        raise ValueError("teleport requires a caster")

    victim: Character
    if target is None:
        victim = caster
    elif isinstance(target, Character):
        victim = target
    else:
        raise TypeError("teleport target must be a Character")

    victim_room = getattr(victim, "room", None)
    if victim_room is None:
        _send_to_char(caster, "You failed.")
        return False

    if _get_room_flags(victim_room) & int(RoomFlag.ROOM_NO_RECALL):
        _send_to_char(caster, "You failed.")
        return False

    if victim is not caster:
        imm_flags = int(getattr(victim, "imm_flags", 0) or 0)
        if imm_flags & int(ImmFlag.SUMMON):
            _send_to_char(caster, "You failed.")
            return False

    if not getattr(caster, "is_npc", True) and getattr(victim, "fighting", None) is not None:
        _send_to_char(caster, "You failed.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if victim is not caster:
        save_level = max(level - 5, 0)
        if saves_spell(save_level, victim, DamageType.OTHER):
            _send_to_char(caster, "You failed.")
            return False

    destination = _get_random_room(victim)
    if destination is None:
        _send_to_char(caster, "You failed.")
        return False

    if victim is not caster:
        _send_to_char(victim, "You have been teleported!")

    victim_name = _character_name(victim)

    broadcast_room(victim_room, f"{victim_name} vanishes!", exclude=victim)
    victim_room.remove_character(victim)
    destination.add_character(victim)
    broadcast_room(destination, f"{victim_name} slowly fades into existence.", exclude=victim)

    view = look(victim)
    if view:
        _send_to_char(victim, view)

    return True


def third_attack(caster, target=None):
    """Stub implementation for third_attack.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def trip(caster: Character, target: Character | None = None) -> str:
    """ROM ``do_trip`` parity: knock an opponent to the ground."""

    if caster is None:
        raise ValueError("trip requires a caster")

    victim = target or getattr(caster, "fighting", None)
    if victim is None:
        _send_to_char(caster, "But you aren't fighting anyone.")
        return ""

    if victim is caster:
        beats = _skill_beats("trip")
        caster.wait = max(int(getattr(caster, "wait", 0) or 0), beats * 2)
        _send_to_char(caster, "You fall flat on your face!")
        room = getattr(caster, "room", None)
        if room is not None:
            message = f"{_character_name(caster)} trips over their own feet!"
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return ""

    chance = _skill_percent(caster, "trip")
    caster_off = int(getattr(caster, "off_flags", 0) or 0)
    caster_level = max(int(getattr(caster, "level", 0) or 0), 0)
    if chance <= 0:
        if bool(getattr(caster, "is_npc", False)) and caster_off & int(OffFlag.TRIP):
            chance = max(chance, 10 + 3 * caster_level)
        else:
            _send_to_char(caster, "Tripping?  What's that?")
            return ""

    if getattr(victim, "is_npc", False):
        opponent = getattr(victim, "fighting", None)
        if opponent is not None and not is_same_group(caster, opponent):
            _send_to_char(caster, "Kill stealing is not permitted.")
            return ""

    if getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.FLYING):
        _send_to_char(caster, "Their feet aren't on the ground.")
        return ""

    if getattr(victim, "position", Position.STANDING) < Position.FIGHTING:
        _send_to_char(caster, f"{_character_name(victim)} is already down.")
        return ""

    if getattr(caster, "has_affect", None) and caster.has_affect(AffectFlag.CHARM):
        if getattr(caster, "master", None) is victim:
            _send_to_char(caster, "They are your beloved master.")
            return ""

    caster_size = int(getattr(caster, "size", 2) or 0)
    victim_size = int(getattr(victim, "size", 2) or 0)
    chance += (caster_size - victim_size) * 10

    caster_dex = caster.get_curr_stat(Stat.DEX) or 0
    victim_dex = victim.get_curr_stat(Stat.DEX) or 0
    chance += caster_dex
    chance -= c_div(victim_dex * 3, 2)

    victim_off = int(getattr(victim, "off_flags", 0) or 0)
    caster_haste = getattr(caster, "has_affect", None) and caster.has_affect(AffectFlag.HASTE)
    victim_haste = getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.HASTE)
    if caster_off & int(OffFlag.FAST) or caster_haste:
        chance += 10
    if victim_off & int(OffFlag.FAST) or victim_haste:
        chance -= 20

    victim_level = max(int(getattr(victim, "level", 0) or 0), 0)
    chance += (caster_level - victim_level) * 2

    beats = _skill_beats("trip")
    roll = rng_mm.number_percent()
    caster_wait = int(getattr(caster, "wait", 0) or 0)

    if roll < chance:
        caster.wait = max(caster_wait, beats)
        victim_name = _character_name(victim)
        caster_name = _character_name(caster)
        _send_to_char(victim, f"{caster_name} trips you and you go down!")
        _send_to_char(caster, f"You trip {victim_name} and {victim_name} goes down!")

        room = getattr(caster, "room", None)
        if room is not None:
            message = f"{caster_name} trips {victim_name}, sending them to the ground."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster or occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)

        from mud.config import get_pulse_violence

        victim.daze = max(int(getattr(victim, "daze", 0) or 0), 2 * get_pulse_violence())
        victim.position = Position.RESTING

        max_damage = max(2, 2 + 2 * victim_size)
        damage = rng_mm.number_range(2, max_damage)
        result = apply_damage(caster, victim, damage, DamageType.BASH, dt="trip")
        if victim.position > Position.STUNNED and getattr(victim, "hit", 0) > 0:
            victim.position = Position.RESTING
        check_improve(caster, "trip", True, 1)
        return result

    fail_wait = c_div(beats * 2, 3)
    caster.wait = max(caster_wait, fail_wait)
    check_improve(caster, "trip", False, 1)
    return apply_damage(caster, victim, 0, DamageType.BASH, dt="trip")


def ventriloquate(caster: Character, target: str | None = None) -> bool:  # noqa: ARG001 - parity signature
    """ROM ``spell_ventriloquate``: throw the caster's voice to a named speaker."""

    if caster is None:
        raise ValueError("ventriloquate requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return False

    argument = (target or "").strip()
    if not argument:
        return False

    parts = argument.split(maxsplit=1)
    speaker = parts[0]
    message = parts[1] if len(parts) > 1 else ""

    if not speaker:
        return False

    normal = f"{speaker} says '{message}'."
    if normal:
        normal = normal[0].upper() + normal[1:]
    reveal = f"Someone makes {speaker} say '{message}'."

    level = max(int(getattr(caster, "level", 0) or 0), 0)

    def _matches_name(candidate: Character | None) -> bool:
        if candidate is None:
            return False
        raw_name = getattr(candidate, "name", "")
        if not raw_name:
            return False
        tokens = [token.strip().lower() for token in str(raw_name).split() if token]
        return speaker.lower() in tokens

    delivered = False
    for occupant in list(getattr(room, "people", []) or []):
        if _matches_name(occupant):
            continue
        position = int(getattr(occupant, "position", Position.STANDING) or 0)
        if position <= int(Position.SLEEPING):
            continue
        saved = saves_spell(level, occupant, DamageType.OTHER)
        payload = reveal if saved else normal
        _send_to_char(occupant, payload)
        delivered = True

    return delivered


def wands(caster, target=None):
    """Stub implementation for wands.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def weaken(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_weaken``: reduce strength and apply the weaken affect."""

    if caster is None or target is None:
        raise ValueError("weaken requires a target")

    if target.has_affect(AffectFlag.WEAKEN) or target.has_spell_effect("weaken"):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if saves_spell(level, target, DamageType.OTHER):
        return False

    duration = c_div(level, 2)
    modifier = -c_div(level, 5)

    effect = SpellEffect(
        name="weaken",
        duration=duration,
        level=level,
        stat_modifiers={Stat.STR: modifier},
        affect_flag=AffectFlag.WEAKEN,
        wear_off_message="You feel stronger.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "You feel your strength slip away.")
    room = getattr(target, "room", None)
    if room is not None:
        message = f"{_character_name(target)} looks tired and weak."
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(message)

    return True


def whip(caster, target=None):
    """Stub implementation for whip.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def word_of_recall(caster: Character, target: Character | None = None) -> bool:
    """Teleport mortals to the temple per ROM ``spell_word_of_recall``."""

    if caster is None:
        raise ValueError("word_of_recall requires a caster")

    victim: Character
    if target is None:
        victim = caster
    elif isinstance(target, Character):
        victim = target
    else:
        raise TypeError("word_of_recall target must be a Character")

    if getattr(victim, "is_npc", True):
        return False

    location = room_registry.get(ROOM_VNUM_TEMPLE)
    if location is None:
        _send_to_char(victim, "You are completely lost.")
        return False

    current_room = getattr(victim, "room", None)

    room_flags = _get_room_flags(current_room)
    if room_flags & int(RoomFlag.ROOM_NO_RECALL):
        _send_to_char(victim, "Spell failed.")
        return False

    if victim.has_affect(AffectFlag.CURSE) or victim.has_spell_effect("curse"):
        _send_to_char(victim, "Spell failed.")
        return False

    if getattr(victim, "fighting", None) is not None:
        stop_fighting(victim, True)

    move_points = int(getattr(victim, "move", 0) or 0)
    victim.move = c_div(move_points, 2)

    victim_name = _character_name(victim)

    if current_room is not None:
        broadcast_room(current_room, f"{victim_name} disappears.", exclude=victim)
        current_room.remove_character(victim)

    location.add_character(victim)
    broadcast_room(location, f"{victim_name} appears in the room.", exclude=victim)

    view = look(victim)
    if view:
        _send_to_char(victim, view)

    return True
