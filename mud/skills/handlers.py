from __future__ import annotations

# Auto-generated skill handlers
# TODO: Replace stubs with actual ROM spell/skill implementations
from types import SimpleNamespace
from typing import Any

from mud.advancement import gain_exp
from mud.affects.saves import check_dispel, saves_dispel, saves_spell
from mud.characters import is_clan_member, is_same_clan, is_same_group
from mud.characters.follow import add_follower, stop_follower
from mud.combat.engine import (
    apply_damage,
    attack_round,
    get_weapon_skill,
    get_weapon_sn,
    get_wielded_weapon,
    is_evil,
    is_good,
    is_neutral,
    set_fighting,
    stop_fighting,
    update_pos,
)
from mud.game_loop import SkyState, weather
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
    LEVEL_HERO,
    LEVEL_IMMORTAL,
    LIQ_WATER,
    LIQUID_TABLE,
    MAX_LEVEL,
    OBJ_VNUM_DISC,
    OBJ_VNUM_LIGHT_BALL,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_PORTAL,
    OBJ_VNUM_ROSE,
    OBJ_VNUM_SPRING,
    ROOM_VNUM_TEMPLE,
    ActFlag,
    AffectFlag,
    ContainerFlag,
    DamageType,
    ExtraFlag,
    ImmFlag,
    ItemType,
    OffFlag,
    PlayerFlag,
    Position,
    RoomFlag,
    Sector,
    Sex,
    Stat,
    VulnFlag,
    WeaponFlag,
    WeaponType,
    WearLocation,
)
from mud.models.obj import Affect, ObjectData
from mud.models.object import Object
from mud.net.protocol import broadcast_room
from mud.registry import room_registry
from mud.skills.metadata import ROM_SKILL_METADATA, ROM_SKILL_NAMES_BY_INDEX
from mud.skills.registry import check_improve
from mud.spawning.obj_spawner import spawn_object
from mud.utils import rng_mm
from mud.world.look import look
from mud.world.movement import _get_random_room
from mud.world.vision import can_see_object, can_see_room, room_is_dark

# ROM const.c lists "spell" as the noun_damage for the cause harm trio.
_CAUSE_SPELL_ATTACK_NOUN = "spell"


_TO_AFFECTS = 0
_TO_OBJECT = 1
_TO_IMMUNE = 2
_TO_RESIST = 3
_TO_VULN = 4
_TO_WEAPON = 5
_APPLY_NONE = 0
_APPLY_AC = 17
_APPLY_HITROLL = 18
_APPLY_DAMROLL = 19
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


def _resolve_trust(char: Character) -> int:
    """Return ROM-style trust falling back to level when unset."""

    trust = _coerce_int(getattr(char, "trust", 0))
    if trust > 0:
        return trust
    return max(_coerce_int(getattr(char, "level", 0)), 0)


def _is_immortal(char: Character) -> bool:
    """Best-effort immortal probe for parity checks."""

    checker = getattr(char, "is_immortal", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:  # pragma: no cover - defensive guard
            return False
    return _resolve_trust(char) >= LEVEL_IMMORTAL


def _room_accessible_without_sight(caster: Character, room: Any) -> bool:
    """Replicate ROM ``can_see_room`` gating without blindness/darkness checks."""

    if room is None:
        return False

    flags = _coerce_int(getattr(room, "room_flags", 0))
    trust = _resolve_trust(caster)
    is_immortal = _is_immortal(caster)

    if flags & int(RoomFlag.ROOM_IMP_ONLY) and trust < MAX_LEVEL:
        return False
    if flags & int(RoomFlag.ROOM_GODS_ONLY) and not is_immortal:
        return False
    if flags & int(RoomFlag.ROOM_HEROES_ONLY) and not is_immortal:
        return False
    if flags & int(RoomFlag.ROOM_NEWBIES_ONLY) and trust > 5 and not is_immortal:
        return False

    room_clan = _coerce_int(getattr(room, "clan", 0))
    caster_clan = _coerce_int(getattr(caster, "clan", 0))
    if room_clan and not is_immortal and room_clan != caster_clan:
        return False

    return True


def _clone_affect_entry(entry: Any) -> Affect | None:
    """Return a copy of an affect-like entry without mutating the source."""

    if isinstance(entry, Affect):
        return Affect(
            where=_coerce_int(getattr(entry, "where", _TO_OBJECT)),
            type=_coerce_int(getattr(entry, "type", 0)),
            level=_coerce_int(getattr(entry, "level", 0)),
            duration=_coerce_int(getattr(entry, "duration", 0)),
            location=_coerce_int(getattr(entry, "location", _APPLY_NONE)),
            modifier=_coerce_int(getattr(entry, "modifier", 0)),
            bitvector=_coerce_int(getattr(entry, "bitvector", 0)),
        )
    if isinstance(entry, dict):
        return Affect(
            where=_coerce_int(entry.get("where", _TO_OBJECT)),
            type=_coerce_int(entry.get("type", 0)),
            level=_coerce_int(entry.get("level", 0)),
            duration=_coerce_int(entry.get("duration", 0)),
            location=_coerce_int(entry.get("location", _APPLY_NONE)),
            modifier=_coerce_int(entry.get("modifier", 0)),
            bitvector=_coerce_int(entry.get("bitvector", 0)),
        )
    return None


def _collect_affects(source: Any, *, clone: bool) -> list[Affect]:
    """Gather affect entries from a source, optionally cloning for safe mutation."""

    affects: list[Affect] = []
    if source is None:
        return affects

    raw_affects = getattr(source, "affected", None)
    if isinstance(raw_affects, list):
        for index, entry in enumerate(list(raw_affects)):
            if isinstance(entry, Affect):
                if clone:
                    clone_entry = _clone_affect_entry(entry)
                    if clone_entry is not None:
                        affects.append(clone_entry)
                else:
                    affects.append(entry)
            elif isinstance(entry, dict):
                converted = _clone_affect_entry(entry)
                if converted is None:
                    continue
                if clone:
                    affects.append(converted)
                else:
                    raw_affects[index] = converted
                    affects.append(converted)

    proto_affects = getattr(source, "affects", None)
    if isinstance(proto_affects, list):
        for entry in proto_affects:
            converted = _clone_affect_entry(entry)
            if converted is not None:
                affects.append(converted)

    return affects


def _copy_base_affects_if_needed(obj: Object | ObjectData, proto: Any) -> None:
    """Copy prototype affects onto an object the first time it is enchanted."""

    if getattr(obj, "enchanted", False):
        return

    base_affects = _collect_affects(proto, clone=True)
    current_affects = _collect_affects(obj, clone=False)

    if base_affects or current_affects:
        obj.affected = base_affects + current_affects
    else:
        obj.affected = []

    obj.enchanted = True


def _object_effective_extra_flags(obj: Object | ObjectData, proto: Any) -> int:
    """Return combined extra flags from instance and prototype."""

    base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
    proto_flags = 0
    if proto is not None:
        proto_flags = _coerce_int(getattr(proto, "extra_flags", 0))
    return base_flags | proto_flags


def _extract_runtime_object(obj: Object | ObjectData) -> None:
    """Remove an object from the world, handling both modern and legacy models."""

    if isinstance(obj, ObjectData):
        from mud.game_loop import _extract_obj as _legacy_extract_obj  # late import to avoid cycles

        _legacy_extract_obj(obj)
        return

    def _prune_from_container(container: Any) -> None:
        contents = getattr(container, "contained_items", None)
        if not isinstance(contents, list):
            return
        if obj in contents:
            contents.remove(obj)
        for child in list(contents):
            _prune_from_container(child)

    location = getattr(obj, "location", None)
    if location is not None:
        contents = getattr(location, "contents", None)
        if isinstance(contents, list) and obj in contents:
            contents.remove(obj)
        if getattr(obj, "location", None) is location:
            obj.location = None

    for character in list(character_registry):
        inventory = getattr(character, "inventory", None)
        removed = False
        if isinstance(inventory, list) and obj in inventory:
            character.remove_object(obj)
            removed = True
        if not removed:
            equipment = getattr(character, "equipment", None)
            if isinstance(equipment, dict):
                for slot, equipped in list(equipment.items()):
                    if equipped is obj:
                        character.remove_object(obj)
                        removed = True
                        break
        for item in list(getattr(character, "inventory", []) or []):
            _prune_from_container(item)
        for item in list(getattr(character, "equipment", {}).values()):
            if item is not None:
                _prune_from_container(item)

    for room in list(room_registry.values()):
        contents = getattr(room, "contents", None)
        if not isinstance(contents, list):
            continue
        if obj in contents:
            contents.remove(obj)
        for item in list(contents):
            _prune_from_container(item)

    contained = getattr(obj, "contained_items", None)
    if isinstance(contained, list):
        contained.clear()


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


def _character_has_affect(character: Character | None, flag: AffectFlag) -> bool:
    """Return True when ``character`` carries the provided affect flag."""

    if character is None:
        return False
    checker = getattr(character, "has_affect", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:  # pragma: no cover - parity guard
            return False
    affected = getattr(character, "affected_by", 0)
    try:
        return bool(int(affected) & int(flag))
    except Exception:  # pragma: no cover - invalid flags fall back to False
        return False


def _effective_extra_flags(obj: Object | ObjectData | None) -> int:
    """Return runtime extra flags including prototype fallbacks."""

    if obj is None:
        return 0
    flags = _coerce_int(getattr(obj, "extra_flags", 0))
    if flags:
        return flags
    proto = getattr(obj, "prototype", None)
    if proto is not None:
        flags = _coerce_int(getattr(proto, "extra_flags", 0))
    return flags


def _object_level(obj: Object | ObjectData | None) -> int:
    """Return the object's effective level mirroring ROM lookups."""

    if obj is None:
        return 0
    try:
        level = int(getattr(obj, "level", 0) or 0)
    except (TypeError, ValueError):
        level = 0
    if level > 0:
        return level
    proto = getattr(obj, "prototype", None)
    try:
        return max(0, int(getattr(proto, "level", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _is_name_match(search: str, candidate: str | None) -> bool:
    """Return True when ``search`` matches ``candidate`` per ROM ``is_name``."""

    if candidate is None:
        return False
    search_text = (search or "").strip().lower()
    candidate_text = candidate.strip().lower()
    if not search_text or not candidate_text:
        return False
    if candidate_text.startswith(search_text):
        return True
    parts = [chunk for chunk in search_text.split() if chunk]
    if not parts:
        return False
    candidate_words = [chunk for chunk in candidate_text.split() if chunk]
    if not candidate_words:
        return False
    for part in parts:
        if not any(word.startswith(part) for word in candidate_words):
            return False
    return True


def _object_name_matches(obj: Object | ObjectData, search: str) -> bool:
    """Return True when any runtime or prototype keyword matches ``search``."""

    candidates: list[str] = []
    for attr_name in ("name", "short_descr"):
        value = getattr(obj, attr_name, None)
        if isinstance(value, str) and value.strip():
            candidates.append(value)
    proto = getattr(obj, "prototype", None)
    if proto is not None:
        for attr_name in ("name", "short_descr"):
            value = getattr(proto, attr_name, None)
            if isinstance(value, str) and value.strip():
                candidates.append(value)
    return any(_is_name_match(search, candidate) for candidate in candidates)


def _iterate_world_objects():
    """Yield (object, holder) pairs mirroring ROM ``object_list`` traversal."""

    seen: set[int] = set()

    def _walk(obj: Object | ObjectData, holder: object):
        ident = id(obj)
        if ident in seen:
            return
        seen.add(ident)
        yield obj, holder
        children: list[Object | ObjectData] = []
        contained = getattr(obj, "contained_items", None)
        if isinstance(contained, list):
            children.extend(contained)
        contains = getattr(obj, "contains", None)
        if isinstance(contains, list):
            children.extend(contains)
        for child in children:
            yield from _walk(child, holder)

    for room in list(room_registry.values()):
        contents = getattr(room, "contents", None)
        if not isinstance(contents, list):
            continue
        for obj in list(contents):
            yield from _walk(obj, room)

    for character in list(character_registry):
        inventory = getattr(character, "inventory", None)
        if isinstance(inventory, list):
            for obj in list(inventory):
                yield from _walk(obj, character)
        equipment = getattr(character, "equipment", None)
        if isinstance(equipment, dict):
            for obj in list(equipment.values()):
                if obj is not None:
                    yield from _walk(obj, character)


def _can_see_object(observer: Character, obj: Object | ObjectData) -> bool:
    """Delegate to shared ROM-style object visibility helper."""

    return can_see_object(observer, obj)


def _can_see_locate_carrier(observer: Character, carrier: Character | None) -> bool:
    """Replicate ROM ``can_see`` semantics for locate object carrier messaging."""

    if observer is None or carrier is None:
        return False
    if observer is carrier:
        return True

    try:
        trust = int(getattr(observer, "trust", 0) or 0)
    except (TypeError, ValueError):
        trust = 0
    if trust <= 0:
        try:
            trust = int(getattr(observer, "level", 0) or 0)
        except (TypeError, ValueError):
            trust = 0

    try:
        invis_level = int(getattr(carrier, "invis_level", 0) or 0)
    except (TypeError, ValueError):
        invis_level = 0
    if trust < invis_level:
        return False

    observer_room = getattr(observer, "room", None)
    carrier_room = getattr(carrier, "room", None)
    try:
        incog_level = int(getattr(carrier, "incog_level", 0) or 0)
    except (TypeError, ValueError):
        incog_level = 0
    if incog_level and observer_room is not carrier_room and trust < incog_level:
        return False

    if not getattr(observer, "is_npc", False):
        act_flags = _coerce_int(getattr(observer, "act", 0))
        if act_flags & int(PlayerFlag.HOLYLIGHT):
            return True
    else:
        immortal_checker = getattr(observer, "is_immortal", None)
        if callable(immortal_checker):
            try:
                if immortal_checker():
                    return True
            except Exception:  # pragma: no cover - parity guard
                pass

    if _character_has_affect(observer, AffectFlag.BLIND):
        return False

    if observer_room is not None and room_is_dark(observer_room):
        if not (
            _character_has_affect(observer, AffectFlag.INFRARED)
            or _character_has_affect(observer, AffectFlag.DARK_VISION)
        ):
            immortal_checker = getattr(observer, "is_immortal", None)
            immortal = False
            if callable(immortal_checker):
                try:
                    immortal = bool(immortal_checker())
                except Exception:  # pragma: no cover - parity guard
                    immortal = False
            else:
                immortal = bool(immortal_checker)
            if not immortal:
                return False

    if _character_has_affect(carrier, AffectFlag.INVISIBLE) and not _character_has_affect(
        observer, AffectFlag.DETECT_INVIS
    ):
        return False

    if (
        _character_has_affect(carrier, AffectFlag.SNEAK)
        and getattr(carrier, "fighting", None) is None
        and not _character_has_affect(observer, AffectFlag.DETECT_HIDDEN)
    ):
        return False

    if (
        _character_has_affect(carrier, AffectFlag.HIDE)
        and getattr(carrier, "fighting", None) is None
        and not _character_has_affect(observer, AffectFlag.DETECT_HIDDEN)
    ):
        return False

    return True


def _format_locate_destination(holder: object, caster: Character) -> str:
    """Return ROM-style location messaging for locate object results."""

    if isinstance(holder, Character):
        if _can_see_locate_carrier(caster, holder):
            return f"One is carried by {_character_name(holder)}."
        return "One is in somewhere."

    if holder is not None:
        room_name = getattr(holder, "name", None) or "somewhere"
        is_immortal = getattr(caster, "is_immortal", None)
        if callable(is_immortal):
            immortal = bool(is_immortal())
        else:
            immortal = bool(is_immortal)
        if immortal:
            vnum = getattr(holder, "vnum", None)
            if vnum is not None:
                return f"One is in {room_name} [Room {vnum}]."
        return f"One is in {room_name}."

    return "One is in somewhere."


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

    if (
        hasattr(caster, "is_immortal")
        and caster.is_immortal()
        and getattr(caster, "level", 0) > LEVEL_IMMORTAL
        and not area
    ):
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
        if (
            area
            and hasattr(victim, "is_immortal")
            and victim.is_immortal()
            and getattr(victim, "level", 0) > LEVEL_IMMORTAL
        ):
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

    if target.has_spell_effect("armor"):
        _send_to_char(caster, "They are already protected.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(name="armor", duration=24, level=level, ac_mod=-20)
    return target.apply_spell_effect(effect)


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


def cancellation(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_cancellation: remove ALL spell effects (no save).

    Mirroring ROM src/magic.c:1033-1203.
    """
    if caster is None or target is None:
        raise ValueError("cancellation requires caster and target")

    # ROM L1039: level += 2
    level = max(int(getattr(caster, "level", 0) or 0), 0) + 2

    # ROM L1041-1047: Type check - only NPC->PC or PC->NPC (except charmed)
    caster_is_npc = getattr(caster, "is_npc", True)
    target_is_npc = getattr(target, "is_npc", True)
    caster_charmed = caster.has_affect(AffectFlag.CHARM) and hasattr(caster, "master")

    if not caster_is_npc and target_is_npc and not (caster_charmed and getattr(caster, "master", None) is target):
        pass  # PC -> NPC allowed
    elif caster_is_npc and not target_is_npc:
        pass  # NPC -> PC allowed
    else:
        _send_to_char(caster, "You failed, try dispel magic.")
        return False

    # ROM L1049: unlike dispel magic, the victim gets NO save
    # ROM L1051-1199: check_dispel on many spells
    found = False
    room = getattr(target, "room", None)

    # Helper to broadcast room messages
    def _broadcast_room_msg(msg: str) -> None:
        if room:
            broadcast_room(room, msg.replace("$n", _character_name(target)), exclude=target)

    def _cancel_effect(effect_name: str) -> bool:
        effect = target.spell_effects.get(effect_name)
        if effect is None:
            return False
        removed = target.remove_spell_effect(effect_name)
        if removed and removed.wear_off_message:
            target.send_to_char(f"{removed.wear_off_message}\n\r")
        return bool(removed)

    if _cancel_effect("armor"):
        found = True

    if _cancel_effect("bless"):
        found = True

    if _cancel_effect("blindness"):
        found = True
        _broadcast_room_msg("$n is no longer blinded.")

    if _cancel_effect("calm"):
        found = True
        _broadcast_room_msg("$n no longer looks so peaceful...")

    if _cancel_effect("change_sex"):
        found = True
        _broadcast_room_msg("$n looks more like $mself again.")

    if _cancel_effect("charm_person"):
        found = True
        _broadcast_room_msg("$n regains $s free will.")

    if _cancel_effect("chill_touch"):
        found = True
        _broadcast_room_msg("$n looks warmer.")

    if _cancel_effect("curse"):
        found = True

    if _cancel_effect("detect_evil"):
        found = True

    if _cancel_effect("detect_good"):
        found = True

    if _cancel_effect("detect_hidden"):
        found = True

    if _cancel_effect("detect_invis"):
        found = True

    if _cancel_effect("detect_magic"):
        found = True

    if _cancel_effect("faerie_fire"):
        _broadcast_room_msg("$n's outline fades.")
        found = True

    if _cancel_effect("fly"):
        _broadcast_room_msg("$n falls to the ground!")
        found = True

    if _cancel_effect("frenzy"):
        _broadcast_room_msg("$n no longer looks so wild.")
        found = True

    if _cancel_effect("giant_strength"):
        _broadcast_room_msg("$n no longer looks so mighty.")
        found = True

    if _cancel_effect("haste"):
        _broadcast_room_msg("$n is no longer moving so quickly.")
        found = True

    if _cancel_effect("infravision"):
        found = True

    if _cancel_effect("invis"):
        _broadcast_room_msg("$n fades into existance.")
        found = True

    if _cancel_effect("mass_invis"):
        _broadcast_room_msg("$n fades into existance.")
        found = True

    if _cancel_effect("pass_door"):
        found = True

    if _cancel_effect("protection_evil"):
        found = True

    if _cancel_effect("protection_good"):
        found = True

    if _cancel_effect("sanctuary"):
        _broadcast_room_msg("The white aura around $n's body vanishes.")
        found = True

    if _cancel_effect("shield"):
        _broadcast_room_msg("The shield protecting $n vanishes.")
        found = True

    if _cancel_effect("sleep"):
        found = True

    if _cancel_effect("slow"):
        _broadcast_room_msg("$n is no longer moving so slowly.")
        found = True

    if _cancel_effect("stone_skin"):
        _broadcast_room_msg("$n's skin regains its normal texture.")
        found = True

    if _cancel_effect("weaken"):
        _broadcast_room_msg("$n looks stronger.")
        found = True

    # ROM L1200-1203: send result message
    if found:
        _send_to_char(caster, "Ok.")
    else:
        _send_to_char(caster, "Spell failed.")

    return found


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
                caster.messages.append("The mayor does not allow charming in the city limits.")
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
    caster_msg = f"{{3You spray {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"
    target_msg = f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light across your vision!{{x"
    room_msg = f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"

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
        caster.level = blind_level
        try:
            blindness(caster, target)
        finally:
            caster.level = original_level

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

        target.extra_flags = extra_flags | int(ExtraFlag.GLOW)
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


def cure_blindness(caster: Character, target: Character | None = None) -> bool:
    """Dispel ROM blindness affect with success/failure messaging."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_blindness requires a target")

    if not (victim.has_affect(AffectFlag.BLIND) or victim.has_spell_effect("blindness")):
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


def cure_critical(caster: Character, target: Character | None = None) -> int:
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


def cure_disease(caster: Character, target: Character | None = None) -> bool:
    """Dispel ROM plague affect with messaging for success/failure."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_disease requires a target")

    if not (victim.has_affect(AffectFlag.PLAGUE) or victim.has_spell_effect("plague")):
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


def cure_poison(caster: Character, target: Character | None = None) -> bool:
    """Dispel ROM poison affect with messaging on outcome."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_poison requires a target")

    if not (victim.has_affect(AffectFlag.POISON) or victim.has_spell_effect("poison")):
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


def cure_serious(caster: Character, target: Character | None = None) -> int:
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
                if occupant is caster or occupant is victim:
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


def enchant_armor(caster: Character, target: Object | ObjectData | None = None) -> bool:
    """ROM ``spell_enchant_armor``: enhance armor AC with ROM failure bands."""

    if caster is None or target is None:
        raise ValueError("enchant_armor requires a caster and armor target")

    if not isinstance(target, (Object, ObjectData)):
        raise TypeError("enchant_armor target must be an Object or ObjectData")

    obj: Object | ObjectData = target
    proto = getattr(obj, "prototype", None) or getattr(obj, "pIndexData", None)

    item_type = _resolve_item_type(getattr(obj, "item_type", None))
    if item_type is None and proto is not None:
        item_type = _resolve_item_type(getattr(proto, "item_type", None))
    if item_type is not ItemType.ARMOR:
        _send_to_char(caster, "That isn't an armor.")
        return False

    if _coerce_int(getattr(obj, "wear_loc", int(WearLocation.NONE))) != int(WearLocation.NONE):
        _send_to_char(caster, "The item must be carried to be enchanted.")
        return False

    fail = 25
    ac_bonus = 0
    ac_found = False

    def _consider_affects(affects: list[Affect]) -> None:
        nonlocal fail, ac_bonus, ac_found
        for affect in affects:
            location = _coerce_int(getattr(affect, "location", _APPLY_NONE))
            modifier = _coerce_int(getattr(affect, "modifier", 0))
            if location == _APPLY_AC:
                ac_bonus = modifier
                ac_found = True
                fail += 5 * (modifier * modifier)
            else:
                fail += 20

    if not getattr(obj, "enchanted", False) and proto is not None:
        _consider_affects(_collect_affects(proto, clone=True))

    object_affects = _collect_affects(obj, clone=False)
    _consider_affects(object_affects)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    fail -= level

    effective_flags = _object_effective_extra_flags(obj, proto)
    if effective_flags & int(ExtraFlag.BLESS):
        fail -= 15
    if effective_flags & int(ExtraFlag.GLOW):
        fail -= 5

    fail = max(5, min(fail, 85))
    result = rng_mm.number_percent()

    short_descr = _object_short_descr(obj)
    room = getattr(caster, "room", None)

    def _notify_room(message: str) -> None:
        if room is not None:
            broadcast_room(room, message, exclude=caster)

    if result < fail // 5:
        _send_to_char(caster, f"{short_descr} flares blindingly... and evaporates!")
        _notify_room(f"{short_descr} flares blindingly... and evaporates!")
        inventory = getattr(caster, "inventory", None)
        removed = False
        if isinstance(inventory, list) and obj in inventory:
            caster.remove_object(obj)
            removed = True
        if not removed:
            equipment = getattr(caster, "equipment", None)
            if isinstance(equipment, dict):
                for slot, equipped in list(equipment.items()):
                    if equipped is obj:
                        caster.remove_object(obj)
                        removed = True
                        break
        _extract_runtime_object(obj)
        return False

    if result < fail // 3:
        _send_to_char(caster, f"{short_descr} glows brightly, then fades...oops.")
        _notify_room(f"{short_descr} glows brightly, then fades.")
        obj.enchanted = True
        obj.affected = []
        obj.extra_flags = 0
        return False

    if result <= fail:
        _send_to_char(caster, "Nothing seemed to happen.")
        return False

    _copy_base_affects_if_needed(obj, proto)
    object_affects = _collect_affects(obj, clone=False)
    obj.affected = object_affects

    if result <= (90 - c_div(level, 5)):
        _send_to_char(caster, f"{short_descr} shimmers with a gold aura.")
        _notify_room(f"{short_descr} shimmers with a gold aura.")
        added = -1
        base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
        obj.extra_flags = base_flags | int(ExtraFlag.MAGIC)
    else:
        _send_to_char(caster, f"{short_descr} glows a brillant gold!")
        _notify_room(f"{short_descr} glows a brillant gold!")
        base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
        obj.extra_flags = base_flags | int(ExtraFlag.MAGIC | ExtraFlag.GLOW)
        added = -2

    obj_level = _coerce_int(getattr(obj, "level", 0))
    if obj_level < LEVEL_HERO:
        obj.level = min(LEVEL_HERO - 1, obj_level + 1)

    updated = False
    for affect in object_affects:
        if _coerce_int(getattr(affect, "location", _APPLY_NONE)) == _APPLY_AC:
            affect.type = 0
            affect.modifier += added
            affect.level = max(_coerce_int(getattr(affect, "level", 0)), level)
            updated = True

    if not updated:
        object_affects.append(
            Affect(
                where=_TO_OBJECT,
                type=0,
                level=level,
                duration=-1,
                location=_APPLY_AC,
                modifier=added,
                bitvector=0,
            )
        )
        obj.affected = object_affects

    return True


def enchant_weapon(caster: Character, target: Object | ObjectData | None = None) -> bool:
    """ROM ``spell_enchant_weapon``: enhance weapon hit/damage modifiers."""

    if caster is None or target is None:
        raise ValueError("enchant_weapon requires a caster and weapon target")

    if not isinstance(target, (Object, ObjectData)):
        raise TypeError("enchant_weapon target must be an Object or ObjectData")

    obj: Object | ObjectData = target
    proto = getattr(obj, "prototype", None) or getattr(obj, "pIndexData", None)

    item_type = _resolve_item_type(getattr(obj, "item_type", None))
    if item_type is None and proto is not None:
        item_type = _resolve_item_type(getattr(proto, "item_type", None))
    if item_type is not ItemType.WEAPON:
        _send_to_char(caster, "That isn't a weapon.")
        return False

    if _coerce_int(getattr(obj, "wear_loc", int(WearLocation.NONE))) != int(WearLocation.NONE):
        _send_to_char(caster, "The item must be carried to be enchanted.")
        return False

    fail = 25
    hit_bonus = 0
    dam_bonus = 0
    hit_found = False
    dam_found = False

    def _consider_affects(affects: list[Affect]) -> None:
        nonlocal fail, hit_bonus, dam_bonus, hit_found, dam_found
        for affect in affects:
            location = _coerce_int(getattr(affect, "location", _APPLY_NONE))
            modifier = _coerce_int(getattr(affect, "modifier", 0))
            if location == _APPLY_HITROLL:
                hit_bonus = modifier
                hit_found = True
                fail += 2 * (modifier * modifier)
            elif location == _APPLY_DAMROLL:
                dam_bonus = modifier
                dam_found = True
                fail += 2 * (modifier * modifier)
            else:
                fail += 25

    if not getattr(obj, "enchanted", False) and proto is not None:
        _consider_affects(_collect_affects(proto, clone=True))

    weapon_affects = _collect_affects(obj, clone=False)
    _consider_affects(weapon_affects)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    fail -= c_div(3 * level, 2)

    effective_flags = _object_effective_extra_flags(obj, proto)
    if effective_flags & int(ExtraFlag.BLESS):
        fail -= 15
    if effective_flags & int(ExtraFlag.GLOW):
        fail -= 5

    fail = max(5, min(fail, 95))
    result = rng_mm.number_percent()

    short_descr = _object_short_descr(obj)
    room = getattr(caster, "room", None)

    def _notify_room(message: str) -> None:
        if room is not None:
            broadcast_room(room, message, exclude=caster)

    if result < fail // 5:
        _send_to_char(caster, f"{short_descr} shivers violently and explodes!")
        _notify_room(f"{short_descr} shivers violently and explodeds!")
        inventory = getattr(caster, "inventory", None)
        removed = False
        if isinstance(inventory, list) and obj in inventory:
            caster.remove_object(obj)
            removed = True
        if not removed:
            equipment = getattr(caster, "equipment", None)
            if isinstance(equipment, dict):
                for slot, equipped in list(equipment.items()):
                    if equipped is obj:
                        caster.remove_object(obj)
                        removed = True
                        break
        _extract_runtime_object(obj)
        return False

    if result < fail // 2:
        _send_to_char(caster, f"{short_descr} glows brightly, then fades...oops.")
        _notify_room(f"{short_descr} glows brightly, then fades.")
        obj.enchanted = True
        obj.affected = []
        obj.extra_flags = 0
        return False

    if result <= fail:
        _send_to_char(caster, "Nothing seemed to happen.")
        return False

    _copy_base_affects_if_needed(obj, proto)
    weapon_affects = _collect_affects(obj, clone=False)
    obj.affected = weapon_affects

    base_flags = _coerce_int(getattr(obj, "extra_flags", 0))
    if result <= (100 - c_div(level, 5)):
        _send_to_char(caster, f"{short_descr} glows blue.")
        _notify_room(f"{short_descr} glows blue.")
        added = 1
        obj.extra_flags = base_flags | int(ExtraFlag.MAGIC)
    else:
        _send_to_char(caster, f"{short_descr} glows a brillant blue!")
        _notify_room(f"{short_descr} glows a brillant blue!")
        added = 2
        obj.extra_flags = base_flags | int(ExtraFlag.MAGIC | ExtraFlag.GLOW)

    obj_level = _coerce_int(getattr(obj, "level", 0))
    if obj_level < LEVEL_HERO - 1:
        obj.level = min(LEVEL_HERO - 1, obj_level + 1)

    hum_needed = False
    dam_updated = False
    hit_updated = False

    for affect in weapon_affects:
        location = _coerce_int(getattr(affect, "location", _APPLY_NONE))
        if location == _APPLY_DAMROLL:
            affect.type = 0
            affect.modifier += added
            affect.level = max(_coerce_int(getattr(affect, "level", 0)), level)
            if affect.modifier > 4:
                hum_needed = True
            dam_updated = True
        elif location == _APPLY_HITROLL:
            affect.type = 0
            affect.modifier += added
            affect.level = max(_coerce_int(getattr(affect, "level", 0)), level)
            if affect.modifier > 4:
                hum_needed = True
            hit_updated = True

    if not dam_updated:
        weapon_affects.append(
            Affect(
                where=_TO_OBJECT,
                type=0,
                level=level,
                duration=-1,
                location=_APPLY_DAMROLL,
                modifier=added,
                bitvector=0,
            )
        )

    if not hit_updated:
        weapon_affects.append(
            Affect(
                where=_TO_OBJECT,
                type=0,
                level=level,
                duration=-1,
                location=_APPLY_HITROLL,
                modifier=added,
                bitvector=0,
            )
        )

    obj.affected = weapon_affects

    if hum_needed:
        obj.extra_flags = _coerce_int(getattr(obj, "extra_flags", 0)) | int(ExtraFlag.HUM)

    return True


def energy_drain(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_energy_drain``: siphon XP, mana, move, and deal damage."""

    if caster is None:
        raise ValueError("energy_drain requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("energy_drain requires a target")

    if victim is not caster:
        alignment = int(getattr(caster, "alignment", 0) or 0)
        caster.alignment = max(-1000, alignment - 50)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if saves_spell(level, victim, DamageType.NEGATIVE):
        _send_to_char(victim, "You feel a momentary chill.")
        return 0

    damage: int
    victim_level = max(int(getattr(victim, "level", 0) or 0), 0)
    if victim_level <= 2:
        damage = int(getattr(caster, "hit", 0) or 0) + 1
    else:
        low = c_div(level, 2)
        high = c_div(3 * level, 2)
        xp_loss = rng_mm.number_range(low, high)
        if xp_loss > 0:
            gain_exp(victim, -xp_loss)

        victim.mana = c_div(int(getattr(victim, "mana", 0) or 0), 2)
        victim.move = c_div(int(getattr(victim, "move", 0) or 0), 2)

        damage = rng_mm.dice(1, max(1, level))
        caster.hit = int(getattr(caster, "hit", 0) or 0) + damage

    _send_to_char(victim, "You feel your life slipping away!")
    _send_to_char(caster, "Wow....what a rush!")

    before = int(getattr(victim, "hit", 0) or 0)
    apply_damage(caster, victim, max(0, damage), DamageType.NEGATIVE, dt="energy drain")
    after = int(getattr(victim, "hit", 0) or 0)
    return max(0, before - after)


def envenom(
    caster: Character,
    target: Character | None = None,
    *,
    item_name: str = "",
) -> dict[str, Any]:
    """ROM do_envenom: poison food/drink or edged weapons.

    Mirroring ROM src/act_obj.c:849-963.

    Returns dict with keys: success (bool), message (str), poisoned_food (bool), poisoned_weapon (bool)
    """
    if caster is None:
        return {"success": False, "message": "No caster"}

    # ROM L856-860: check for argument
    if not item_name:
        return {"success": False, "message": "Envenom what item?"}

    # ROM L862-868: find object in inventory
    obj = None
    inventory = list(getattr(caster, "inventory", []) or [])
    for candidate in inventory:
        obj_name = getattr(candidate, "name", None) or getattr(getattr(candidate, "prototype", None), "name", "")
        if obj_name and item_name.lower() in obj_name.lower():
            obj = candidate
            break

    if obj is None:
        return {"success": False, "message": "You don't have that item."}

    # ROM L870-874: check skill
    caster_skill = int(getattr(caster, "skills", {}).get("envenom", 0))
    if caster_skill < 1:
        return {"success": False, "message": "Are you crazy? You'd poison yourself!"}

    proto = getattr(obj, "prototype", None)
    obj_item_type = getattr(obj, "item_type", None) or getattr(proto, "item_type", None)

    # Resolve item type
    if isinstance(obj_item_type, str):
        try:
            obj_item_type = ItemType[obj_item_type.upper()]
        except (KeyError, AttributeError):
            obj_item_type = None
    elif isinstance(obj_item_type, int):
        try:
            obj_item_type = ItemType(obj_item_type)
        except ValueError:
            obj_item_type = None

    # ROM L876-903: poison food/drink
    if obj_item_type in (ItemType.FOOD, ItemType.DRINK_CON):
        # ROM L878-883: check for blessed/fireproof
        obj_extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        proto_extra_flags = int(getattr(proto, "extra_flags", 0) or 0)
        effective_flags = obj_extra_flags | proto_extra_flags

        if (effective_flags & int(ExtraFlag.BLESS)) or (effective_flags & int(ExtraFlag.BURN_PROOF)):
            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            return {"success": False, "message": f"You fail to poison {short_descr}."}

        # ROM L885-896: success check
        values = list(getattr(obj, "value", [0, 0, 0, 0]))
        while len(values) < 4:
            values.append(0)

        percent = rng_mm.number_percent()
        if percent < caster_skill:
            # Success!
            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            room = getattr(caster, "room", None)
            if room is not None:
                broadcast_room(
                    room, f"{_character_name(caster)} treats {short_descr} with deadly poison.", exclude=caster
                )

            _send_to_char(caster, f"You treat {short_descr} with deadly poison.")

            if not values[3]:
                values[3] = 1
                obj.value = values
                check_improve(caster, "envenom", True, 4)

            # ROM L894: WAIT_STATE
            return {"success": True, "message": "", "poisoned_food": True}

        # ROM L898-902: failure
        short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
        if values[3] == 0:
            check_improve(caster, "envenom", False, 4)

        return {"success": False, "message": f"You fail to poison {short_descr}.", "poisoned_food": False}

    # ROM L905-959: poison weapon
    if obj_item_type == ItemType.WEAPON:
        obj_extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        proto_extra_flags = int(getattr(proto, "extra_flags", 0) or 0)
        effective_flags = obj_extra_flags | proto_extra_flags

        # ROM L907-918: check weapon flags
        weapon_flags = 0
        for aff in list(getattr(obj, "affected", []) or []):
            where = int(getattr(aff, "where", 0) or 0)
            if where == _TO_WEAPON:
                weapon_flags |= int(getattr(aff, "bitvector", 0) or 0)

        forbidden_flags = (
            int(WeaponFlag.FLAMING)
            | int(WeaponFlag.FROST)
            | int(WeaponFlag.VAMPIRIC)
            | int(WeaponFlag.SHARP)
            | int(WeaponFlag.VORPAL)
            | int(WeaponFlag.SHOCKING)
        )

        if (
            (weapon_flags & forbidden_flags)
            or (effective_flags & int(ExtraFlag.BLESS))
            or (effective_flags & int(ExtraFlag.BURN_PROOF))
        ):
            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            return {"success": False, "message": f"You can't seem to envenom {short_descr}."}

        # ROM L920-925: check for edged weapon
        values = list(getattr(obj, "value", [0, 0, 0, 0]))
        while len(values) < 4:
            values.append(0)

        weapon_attack_type = int(values[3] if len(values) > 3 else 0)
        if weapon_attack_type < 0:
            return {"success": False, "message": "You can only envenom edged weapons."}

        # ROM L927-931: check if already poisoned
        if weapon_flags & int(WeaponFlag.POISON):
            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            return {"success": False, "message": f"{short_descr} is already envenomed."}

        # ROM L933-951: success check
        percent = rng_mm.number_percent()
        if percent < caster_skill:
            # ROM L937-944: create poison affect
            level = max(int(getattr(caster, "level", 0) or 0), 0)
            duration = c_div(level * percent, 100 * 2)
            affect_level = c_div(level * percent, 100)

            poison_affect = Affect(
                where=_TO_WEAPON,
                type=-1,  # ROM uses gsn_poison but we use -1 for object affects
                level=affect_level,
                duration=duration,
                location=0,
                modifier=0,
                bitvector=int(WeaponFlag.POISON),
            )

            if not hasattr(obj, "affected") or obj.affected is None:
                obj.affected = []
            obj.affected.append(poison_affect)

            # ROM L946-948: messages
            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            room = getattr(caster, "room", None)
            if room is not None:
                broadcast_room(
                    room, f"{_character_name(caster)} coats {short_descr} with deadly venom.", exclude=caster
                )

            _send_to_char(caster, f"You coat {short_descr} with venom.")
            check_improve(caster, "envenom", True, 3)

            return {"success": True, "message": "", "poisoned_weapon": True}

        # ROM L952-958: failure
        short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
        check_improve(caster, "envenom", False, 3)
        return {"success": False, "message": f"You fail to envenom {short_descr}.", "poisoned_weapon": False}

    # ROM L961-962: can't poison this type
    short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
    return {"success": False, "message": f"You can't poison {short_descr}."}


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


def farsight(
    caster: Character,
    target: Character | None = None,
    *,
    direction: str = "",
) -> str:
    """ROM spell_farsight: magical scan if not blind.

    Mirroring ROM src/magic2.c:44-53.
    """
    if caster is None:
        raise ValueError("farsight requires a caster")

    # ROM L46-50: blind check
    if caster.has_affect(AffectFlag.BLIND):
        _send_to_char(caster, "Maybe it would help if you could see?")
        return ""

    # ROM L52: do_function(ch, &do_scan, target_name)
    from mud.commands.inspection import do_scan

    result = do_scan(caster, direction)
    if result:
        _send_to_char(caster, result)
    return result


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
    affect.spell_name = "fireproof"
    affect.wear_off_message = _OBJECT_FIREPROOF_WEAR_OFF

    affects = getattr(obj, "affected", None)
    if isinstance(affects, list):
        affects.append(affect)
    else:
        obj.affected = [affect]

    obj.extra_flags = extra_flags | int(ExtraFlag.BURN_PROOF)

    message = f"{_object_short_descr(obj)} is surrounded by a protective aura."
    _send_to_char(caster, f"You protect {_object_short_descr(obj)} from fire.")

    room = getattr(caster, "room", None)
    if room is not None:
        broadcast_room(room, message, exclude=caster)

    return True


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

    if (
        (caster_good and not target_good)
        or (caster_neutral and not target_neutral)
        or (caster_evil and not target_evil)
    ):
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


def general_purpose(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> int:
    """ROM ``spell_general_purpose`` wand projectile damage."""

    if caster is None or target is None:
        raise ValueError("general_purpose requires caster and target")

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(int(base_level or 0), 0)
    roll = rng_mm.number_range(25, 100)
    damage = roll
    if saves_spell(level, target, DamageType.PIERCE):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(
        caster,
        target,
        max(0, damage),
        DamageType.PIERCE,
        dt="general purpose ammo",
    )
    after = int(getattr(target, "hit", 0) or 0)
    return max(0, before - after)


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


def haggle(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """ROM haggle: passive skill checked during shop buy/sell transactions.

    Mirroring ROM src/act_obj.c:2601-2933 (three inline checks).

    Haggle is not a command - it's a passive skill checked in:
    - do_buy (L2722-2730): reduces purchase cost
    - do_sell (L2924-2933): increases sale price
    - pet shop (L2601-2609): reduces pet cost

    This function should never be called directly as a skill command.
    """
    return {
        "success": False,
        "message": "Haggle is a passive skill used automatically when buying or selling at shops.",
    }


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


def harm(caster: Character, target: Character | None = None) -> int:
    """ROM spell_harm: damage spell that reduces target to near-death.

    Mirroring ROM src/magic.c:3048-3059.
    """
    if caster is None or target is None:
        raise ValueError("harm requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    target_hit = int(getattr(target, "hit", 0) or 0)

    # ROM L3053: dam = UMAX(20, victim->hit - dice(1,4))
    dice_roll = rng_mm.dice(1, 4)
    dam = max(20, target_hit - dice_roll)

    # ROM L3054-3055: save reduces to min(50, dam/2)
    if saves_spell(level, target, DamageType.HARM):
        dam = min(50, c_div(dam, 2))

    # ROM L3056: cap at 100
    dam = min(100, dam)

    # ROM L3057: damage(ch, victim, dam, sn, DAM_HARM, TRUE)
    target.hit -= dam
    update_pos(target)
    return dam


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


def heat_metal(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> int:
    """ROM spell_heat_metal: heat metal items causing victim to drop or take damage.

    Mirroring ROM src/magic.c:3123-3277.
    """
    if caster is None or target is None:
        raise ValueError("heat_metal requires caster and target")

    level = override_level if override_level is not None else max(int(getattr(caster, "level", 0) or 0), 0)
    dam = 0
    fail = True

    # ROM L3131-3132: check saves and fire immunity
    victim_imm = int(getattr(target, "imm_flags", 0) or 0)
    if saves_spell(level + 2, target, DamageType.FIRE) or (victim_imm & ImmFlag.FIRE):
        _send_to_char(caster, "Your spell had no effect.")
        _send_to_char(target, "You feel momentarily warmer.")
        return 0

    # ROM L3134-3263: iterate through victim's inventory
    room = getattr(target, "room", None)
    inventory = list(getattr(target, "inventory", []) or [])
    equipment = dict(getattr(target, "equipment", {}) or {})

    # Combine inventory and equipped items for iteration
    all_items = inventory + list(equipment.values())

    for obj in all_items:
        # ROM L3138-3141: check if item should be heated
        obj_level = int(getattr(obj, "level", 0) or 0)
        if not (rng_mm.number_range(1, 2 * level) > obj_level):
            continue
        if saves_spell(level, target, DamageType.FIRE):
            continue

        obj_extra = int(getattr(obj, "extra_flags", 0) or 0)
        if (obj_extra & ExtraFlag.NONMETAL) or (obj_extra & ExtraFlag.BURN_PROOF):
            continue

        obj_type = getattr(obj, "item_type", None)
        if obj_type is None and hasattr(obj, "prototype"):
            obj_type = getattr(obj.prototype, "item_type", None)
        wear_loc = int(getattr(obj, "wear_loc", -1))
        is_worn = wear_loc != -1

        # ROM L3143-3261: handle ARMOR and WEAPON types
        if obj_type == ItemType.ARMOR:
            if is_worn:
                # ROM L3146-3175: try to remove worn armor
                obj_weight = int(getattr(obj, "weight", 0) or 0)
                dex = int(getattr(target, "dex", 10) or 10)
                can_remove = c_div(obj_weight, 10) < rng_mm.number_range(1, 2 * dex)

                # Simplified: assume can_drop_obj returns True (no cursed items check)
                if can_remove:
                    # Successfully removed
                    obj_name = getattr(obj, "short_descr", "something")
                    if room:
                        broadcast_room(
                            room,
                            f"{_character_name(target)} yelps and throws {obj_name} to the ground!",
                            exclude=target,
                        )
                    _send_to_char(target, f"You remove and drop {obj_name} before it burns you.")
                    dam += c_div(rng_mm.number_range(1, obj_level), 3)

                    # Move from equipped to room
                    for slot, equipped in list(equipment.items()):
                        if equipped is obj:
                            del target.equipment[slot]
                            break
                    if room and hasattr(room, "objects"):
                        room.objects.append(obj)
                    fail = False
                else:
                    # ROM L3167-3174: stuck on body
                    obj_name = getattr(obj, "short_descr", "something")
                    _send_to_char(target, f"Your skin is seared by {obj_name}!")
                    dam += rng_mm.number_range(1, obj_level)
                    fail = False
            else:
                # ROM L3177-3201: not worn, try to drop from inventory
                obj_name = getattr(obj, "short_descr", "something")
                # Simplified: assume can_drop (no cursed check)
                if True:  # can_drop_obj
                    if room:
                        broadcast_room(
                            room,
                            f"{_character_name(target)} yelps and throws {obj_name} to the ground!",
                            exclude=target,
                        )
                    _send_to_char(target, f"You and drop {obj_name} before it burns you.")
                    dam += c_div(rng_mm.number_range(1, obj_level), 6)

                    if obj in target.inventory:
                        target.inventory.remove(obj)
                    if room and hasattr(room, "objects"):
                        room.objects.append(obj)
                    fail = False
                else:
                    # Cannot drop
                    _send_to_char(target, f"Your skin is seared by {obj_name}!")
                    dam += c_div(rng_mm.number_range(1, obj_level), 2)
                    fail = False

        elif obj_type == ItemType.WEAPON:
            # ROM L3204-3260: handle weapons
            if is_worn:
                # ROM L3206-3207: skip flaming weapons
                obj_weapon_flags = int(
                    getattr(obj, "value", [0, 0, 0, 0])[3]
                    if hasattr(obj, "value") and len(getattr(obj, "value", [])) > 3
                    else 0
                )
                if obj_weapon_flags & WeaponFlag.FLAMING:
                    continue

                # Try to drop wielded weapon
                obj_name = getattr(obj, "short_descr", "something")
                # Simplified: assume can_drop
                if True:  # can_drop_obj and remove_obj
                    if room:
                        broadcast_room(
                            room,
                            f"{_character_name(target)} is burned by {obj_name}, and throws it to the ground.",
                            exclude=target,
                        )
                    _send_to_char(target, "You throw your red-hot weapon to the ground!")
                    dam += 1

                    # Unequip weapon
                    for slot, equipped in list(equipment.items()):
                        if equipped is obj:
                            del target.equipment[slot]
                            break
                    if room and hasattr(room, "objects"):
                        room.objects.append(obj)
                    fail = False
                else:
                    # ROM L3224-3232: stuck with weapon
                    _send_to_char(target, "Your weapon sears your flesh!")
                    dam += rng_mm.number_range(1, obj_level)
                    fail = False
            else:
                # ROM L3234-3259: weapon in inventory
                obj_name = getattr(obj, "short_descr", "something")
                if True:  # can_drop_obj
                    if room:
                        broadcast_room(
                            room,
                            f"{_character_name(target)} throws a burning hot {obj_name} to the ground!",
                            exclude=target,
                        )
                    _send_to_char(target, f"You and drop {obj_name} before it burns you.")
                    dam += c_div(rng_mm.number_range(1, obj_level), 6)

                    if obj in target.inventory:
                        target.inventory.remove(obj)
                    if room and hasattr(room, "objects"):
                        room.objects.append(obj)
                    fail = False
                else:
                    # Cannot drop
                    _send_to_char(target, f"Your skin is seared by {obj_name}!")
                    dam += c_div(rng_mm.number_range(1, obj_level), 2)
                    fail = False

    # ROM L3265-3276: final damage application
    if fail:
        _send_to_char(caster, "Your spell had no effect.")
        _send_to_char(target, "You feel momentarily warmer.")
        return 0
    else:
        # ROM L3273-3275: save for reduced damage
        if saves_spell(level, target, DamageType.FIRE):
            dam = c_div(2 * dam, 3)

        # Apply damage
        target.hit -= dam
        update_pos(target)
        return dam


def hide(caster: Character, target: Character | None = None) -> str:
    """ROM do_hide - attempt to hide from observers.

    Mirrors ROM src/act_move.c:1526-1542 (do_hide).

    Logic:
    - Send message "You attempt to hide."
    - Remove existing AFF_HIDE if present (L1530-1531)
    - Roll: number_percent() < get_skill(ch, gsn_hide) (L1533)
    - On success: SET_BIT(ch->affected_by, AFF_HIDE) (L1535)
    - check_improve() on both success and failure (L1536, 1539)

    Args:
        caster: Character attempting to hide
        target: Unused (parity signature)

    Returns:
        Message string
    """
    from mud.utils import rng_mm

    if caster is None:
        raise ValueError("hide requires a caster")

    # ROM L1528: send_to_char("You attempt to hide.\n\r", ch);
    _send_to_char(caster, "You attempt to hide.")

    # ROM L1530-1531: if (IS_AFFECTED(ch, AFF_HIDE)) REMOVE_BIT(ch->affected_by, AFF_HIDE);
    if caster.has_affect(AffectFlag.HIDE):
        caster.remove_affect(AffectFlag.HIDE)

    # ROM L1533: if (number_percent() < get_skill(ch, gsn_hide))
    skill_pct = _skill_percent(caster, "hide")
    roll = rng_mm.number_percent()

    if roll < skill_pct:
        # ROM L1535: SET_BIT(ch->affected_by, AFF_HIDE);
        affected_by = int(getattr(caster, "affected_by", 0) or 0)
        caster.affected_by = affected_by | int(AffectFlag.HIDE)

        # ROM L1536: check_improve(ch, gsn_hide, TRUE, 3);
        check_improve(caster, "hide", success=True, multiplier=3)
    else:
        # ROM L1539: check_improve(ch, gsn_hide, FALSE, 3);
        check_improve(caster, "hide", success=False, multiplier=3)

    return "You attempt to hide."


def high_explosive(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> int:
    """ROM ``spell_high_explosive`` wand projectile damage."""

    if caster is None or target is None:
        raise ValueError("high_explosive requires caster and target")

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(int(base_level or 0), 0)
    roll = rng_mm.number_range(30, 120)
    damage = roll
    if saves_spell(level, target, DamageType.PIERCE):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(
        caster,
        target,
        max(0, damage),
        DamageType.PIERCE,
        dt="high explosive ammo",
    )
    after = int(getattr(target, "hit", 0) or 0)
    return max(0, before - after)


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
        affect.spell_name = "invisibility"
        affect.wear_off_message = _OBJECT_INVIS_WEAR_OFF

        affects = getattr(obj, "affected", None)
        if isinstance(affects, list):
            affects.append(affect)
        else:
            obj.affected = [affect]

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


def know_alignment(caster: Character, target: Character | None = None) -> str:
    """ROM ``spell_know_alignment`` aura messaging based on alignment bands."""

    if caster is None:
        raise ValueError("know_alignment requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("know_alignment requires a target")

    alignment = int(getattr(victim, "alignment", 0) or 0)
    name = _character_name(victim)
    possessive = _possessive_pronoun(victim)

    def _choose(other: str, self_msg: str) -> str:
        return self_msg if victim is caster else other

    if alignment > 700:
        message = _choose(f"{name} has a pure and good aura.", "You have a pure and good aura.")
    elif alignment > 350:
        message = _choose(f"{name} is of excellent moral character.", "You are of excellent moral character.")
    elif alignment > 100:
        message = _choose(f"{name} is often kind and thoughtful.", "You are often kind and thoughtful.")
    elif alignment > -100:
        message = _choose(f"{name} doesn't have a firm moral commitment.", "You don't have a firm moral commitment.")
    elif alignment > -350:
        message = _choose(f"{name} lies to {possessive} friends.", "You lie to your friends.")
    elif alignment > -700:
        message = _choose(f"{name} is a black-hearted murderer.", "You are a black-hearted murderer.")
    else:
        message = _choose(f"{name} is the embodiment of pure evil!", "You are the embodiment of pure evil!")

    _send_to_char(caster, message)
    return message


def lightning_bolt(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_lightning_bolt``: level-scaled lightning damage."""

    if caster is None or target is None:
        raise ValueError("lightning_bolt requires a caster and target")

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
        25,
        28,
        31,
        34,
        37,
        40,
        40,
        41,
        42,
        42,
        43,
        44,
        44,
        45,
        46,
        46,
        47,
        48,
        48,
        49,
        50,
        50,
        51,
        52,
        52,
        53,
        54,
        54,
        55,
        56,
        56,
        57,
        58,
        58,
        59,
        60,
        60,
        61,
        62,
        62,
        63,
        64,
    )
    index = min(level, len(dam_each) - 1)
    base = dam_each[index]
    low = c_div(base, 2)
    high = base * 2
    roll = rng_mm.number_range(low, high)

    damage = roll
    if saves_spell(level, target, DamageType.LIGHTNING):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(caster, target, max(0, damage), DamageType.LIGHTNING, dt="lightning bolt")
    after = int(getattr(target, "hit", 0) or 0)
    return max(0, before - after)


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


def locate_object(caster: Character, target: str | None = None) -> bool:
    """ROM ``spell_locate_object``: reveal locations of matching objects."""

    if caster is None:
        raise ValueError("locate_object requires a caster")

    argument = ""
    if isinstance(target, str):
        argument = target.strip()

    if not argument:
        _send_to_char(caster, "Nothing like that in heaven or earth.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    max_found = 200 if caster.is_immortal() else 2 * level

    results: list[str] = []
    detection_threshold = max(0, min(level * 2, 100))

    for obj, holder in _iterate_world_objects():
        if not _object_name_matches(obj, argument):
            continue
        if not _can_see_object(caster, obj):
            continue
        if _effective_extra_flags(obj) & int(ExtraFlag.NOLOCATE):
            continue
        if not caster.is_immortal() and level < _object_level(obj):
            continue
        if rng_mm.number_percent() > detection_threshold:
            continue

        results.append(_format_locate_destination(holder, caster))
        if max_found >= 0 and len(results) >= max_found:
            break

    if not results:
        _send_to_char(caster, "Nothing like that in heaven or earth.")
        return False

    for line in results:
        if line:
            formatted = line[0].upper() + line[1:]
        else:
            formatted = line
        _send_to_char(caster, formatted)
    return True


def lore(caster: Character, target: Object | ObjectData | None = None) -> bool:
    """ROM ``do_lore`` skill: chance-based appraisal using identify output."""

    if caster is None:
        raise ValueError("lore requires a caster")
    if target is None:
        raise ValueError("lore requires an object target")
    if not isinstance(target, (Object, ObjectData)):
        raise TypeError("lore target must be an object")

    beats = _skill_beats("lore")
    caster.wait = max(int(getattr(caster, "wait", 0) or 0), beats)

    chance = _skill_percent(caster, "lore")
    if chance <= 0:
        _send_to_char(caster, "You don't know anything about that.")
        return False

    roll = rng_mm.number_percent()
    if roll <= chance:
        check_improve(caster, "lore", True, 1)
        return identify(caster, target)

    _send_to_char(caster, "You can't glean any information about it.")
    check_improve(caster, "lore", False, 1)
    return False


def magic_missile(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_magic_missile``: level tabled energy bolts."""

    if caster is None or target is None:
        raise ValueError("magic_missile requires a caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    dam_each = (
        0,
        3,
        3,
        4,
        4,
        5,
        6,
        6,
        6,
        6,
        6,
        7,
        7,
        7,
        7,
        7,
        8,
        8,
        8,
        8,
        8,
        9,
        9,
        9,
        9,
        9,
        10,
        10,
        10,
        10,
        10,
        11,
        11,
        11,
        11,
        11,
        12,
        12,
        12,
        12,
        12,
        13,
        13,
        13,
        13,
        13,
        14,
        14,
        14,
        14,
        14,
    )
    index = min(level, len(dam_each) - 1)
    base = dam_each[index]
    low = c_div(base, 2)
    high = base * 2
    roll = rng_mm.number_range(low, high)

    damage = roll
    if saves_spell(level, target, DamageType.ENERGY):
        damage = c_div(damage, 2)

    before = int(getattr(target, "hit", 0) or 0)
    apply_damage(caster, target, max(0, damage), DamageType.ENERGY, dt="magic missile")
    after = int(getattr(target, "hit", 0) or 0)
    return max(0, before - after)


def mass_healing(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_mass_healing: cast heal and refresh on same-type room occupants.

    Mirroring ROM src/magic.c:3807-3824.
    """
    if caster is None:
        raise ValueError("mass_healing requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return False

    # ROM L3816-3822: iterate room people and cast on same type
    # (IS_NPC(ch) && IS_NPC(gch)) || (!IS_NPC(ch) && !IS_NPC(gch))
    caster_is_npc = getattr(caster, "is_npc", True)
    healed = False

    for occupant in list(getattr(room, "people", []) or []):
        occupant_is_npc = getattr(occupant, "is_npc", True)
        # Only heal if both are NPCs or both are PCs
        if caster_is_npc == occupant_is_npc:
            # ROM L3820-3821: cast heal and refresh on the target
            heal(caster, occupant)
            refresh(caster, occupant)
            healed = True

    return healed


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


def nexus(caster: Character, target: Character | None = None) -> list[Object]:
    """ROM ``spell_nexus``: raise paired portals linking caster and target rooms."""

    if caster is None or target is None:
        raise ValueError("nexus requires a target")
    if not isinstance(target, Character):
        raise TypeError("nexus target must be a Character")

    from_room = getattr(caster, "room", None)
    to_room = getattr(target, "room", None)

    def _fail() -> list[Object]:
        _send_to_char(caster, "You failed.")
        return []

    if from_room is None or to_room is None or target is caster:
        return _fail()

    if not can_see_room(caster, to_room):
        return _fail()
    if not can_see_room(caster, from_room):
        return _fail()

    def _room_flags(room) -> int:
        return _coerce_int(getattr(room, "room_flags", 0))

    from_flags = _room_flags(from_room)
    to_flags = _room_flags(to_room)

    target_disallowed = (
        int(RoomFlag.ROOM_SAFE)
        | int(RoomFlag.ROOM_PRIVATE)
        | int(RoomFlag.ROOM_SOLITARY)
        | int(RoomFlag.ROOM_NO_RECALL)
    )
    origin_disallowed = int(RoomFlag.ROOM_SAFE) | int(RoomFlag.ROOM_NO_RECALL)

    if to_flags & target_disallowed:
        return _fail()
    if from_flags & origin_disallowed:
        return _fail()

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    target_level = max(_coerce_int(getattr(target, "level", 0)), 0)
    if target_level >= level + 3:
        return _fail()

    if is_clan_member(target) and not is_same_clan(caster, target):
        return _fail()

    target_is_npc = bool(getattr(target, "is_npc", True))
    if not target_is_npc and target_level >= LEVEL_HERO:
        return _fail()

    if target_is_npc:
        imm_flags = _coerce_int(getattr(target, "imm_flags", 0))
        if imm_flags & int(ImmFlag.SUMMON):
            return _fail()
        if saves_spell(level, target, int(DamageType.NONE)):
            return _fail()

    held_obj = getattr(caster, "equipment", {}).get("hold") if hasattr(caster, "equipment") else None
    held_type = _resolve_item_type(getattr(held_obj, "item_type", None))
    if held_type is None and getattr(held_obj, "prototype", None) is not None:
        held_type = _resolve_item_type(getattr(held_obj.prototype, "item_type", None))

    if not caster.is_immortal():
        if held_obj is None or held_type is not ItemType.WARP_STONE:
            _send_to_char(caster, "You lack the proper component for this spell.")
            return []

    if held_obj is not None and held_type is ItemType.WARP_STONE:
        stone_name = _object_short_descr(held_obj)
        _send_to_char(caster, f"You draw upon the power of {stone_name}.")
        _send_to_char(caster, "It flares brightly and vanishes!")
        if hasattr(caster, "remove_object"):
            caster.remove_object(held_obj)
        if hasattr(held_obj, "location"):
            held_obj.location = None

    created: list[Object] = []

    portal_out = spawn_object(OBJ_VNUM_PORTAL)
    if portal_out is None:
        return _fail()

    timer = 1 + c_div(level, 10)
    portal_out.timer = timer
    if not isinstance(portal_out.value, list):
        portal_out.value = [0, 0, 0, 0, 0]
    while len(portal_out.value) <= 3:
        portal_out.value.append(0)
    portal_out.value[3] = _coerce_int(getattr(to_room, "vnum", 0))
    from_room.add_object(portal_out)

    portal_name = _object_short_descr(portal_out)
    broadcast_room(from_room, f"{portal_name} rises up from the ground.", exclude=caster)
    _send_to_char(caster, f"{portal_name} rises up before you.")
    created.append(portal_out)

    if to_room is from_room:
        return created

    portal_return = spawn_object(OBJ_VNUM_PORTAL)
    if portal_return is None:
        return created

    portal_return.timer = timer
    if not isinstance(portal_return.value, list):
        portal_return.value = [0, 0, 0, 0, 0]
    while len(portal_return.value) <= 3:
        portal_return.value.append(0)
    portal_return.value[3] = _coerce_int(getattr(from_room, "vnum", 0))
    to_room.add_object(portal_return)

    return_name = _object_short_descr(portal_return)
    broadcast_room(to_room, f"{return_name} rises up from the ground.")
    created.append(portal_return)

    return created


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


def peek(caster: Character, target: Character | None = None) -> dict[str, any]:
    """ROM peek skill: chance to see victim's inventory when looking at them.

    Mirroring ROM src/act_info.c:501-507 (show_char_to_char_1).

    Returns dict with keys: success (bool), inventory (list[Object]), message (str)
    """
    if caster is None or target is None:
        return {"success": False, "message": "No target to peek at"}

    # ROM L501-502: peek only works on others, only for PCs
    if target is caster:
        return {"success": False, "message": "You can see your own inventory"}

    caster_is_npc = getattr(caster, "is_npc", True)
    if caster_is_npc:
        return {"success": False, "message": "NPCs don't peek"}

    # ROM L502: skill check - number_percent() < get_skill(ch, gsn_peek)
    caster_skill = int(getattr(caster, "skills", {}).get("peek", 0))
    percent = rng_mm.number_percent()

    if percent >= caster_skill:
        return {"success": False, "message": "You failed to peek"}

    # ROM L504-506: success - show inventory
    inventory = list(getattr(target, "inventory", []) or [])

    return {
        "success": True,
        "inventory": inventory,
        "message": f"You peek at {getattr(target, 'name', 'someone')}'s inventory",
    }


def pick_lock(
    caster: Character,
    target: Character | None = None,
    *,
    target_name: str = "",
) -> dict[str, Any]:
    """ROM do_pick: unlock doors, portals, or containers with skill check.

    Mirroring ROM src/act_move.c:841-991.

    Returns dict with keys: success (bool), message (str), picked_type (str)
    """
    if caster is None:
        return {"success": False, "message": "No caster"}

    if not target_name:
        return {"success": False, "message": "Pick what?"}

    caster_skill = int(getattr(caster, "skills", {}).get("pick lock", 0))
    caster_is_npc = getattr(caster, "is_npc", True)

    room = getattr(caster, "room", None)
    if room is None:
        return {"success": False, "message": "You're not in a room."}

    people = list(getattr(room, "people", []) or [])
    caster_level = int(getattr(caster, "level", 0) or 0)

    for guard in people:
        if guard is caster:
            continue
        if not getattr(guard, "is_npc", False):
            continue
        awake_positions = {Position.STANDING, Position.SITTING, Position.FIGHTING, Position.RESTING}
        guard_pos = getattr(guard, "position", Position.STANDING)
        if guard_pos not in awake_positions:
            continue
        guard_level = int(getattr(guard, "level", 0) or 0)
        if caster_level + 5 < guard_level:
            guard_name = _character_name(guard)
            return {"success": False, "message": f"{guard_name} is standing too close to the lock."}

    percent = rng_mm.number_percent()
    if not caster_is_npc and percent > caster_skill:
        _send_to_char(caster, "You failed.")
        check_improve(caster, "pick lock", False, 2)
        return {"success": False, "message": ""}

    obj = None
    inventory = list(getattr(caster, "inventory", []) or [])
    for candidate in inventory:
        obj_name = getattr(candidate, "name", None) or getattr(getattr(candidate, "prototype", None), "name", "")
        if obj_name and target_name.lower() in obj_name.lower():
            obj = candidate
            break

    if obj is None:
        room_contents = list(getattr(room, "contents", []) or [])
        for candidate in room_contents:
            obj_name = getattr(candidate, "name", None) or getattr(getattr(candidate, "prototype", None), "name", "")
            if obj_name and target_name.lower() in obj_name.lower():
                obj = candidate
                break

    if obj is not None:
        proto = getattr(obj, "prototype", None)
        obj_item_type = getattr(obj, "item_type", None) or getattr(proto, "item_type", None)

        if isinstance(obj_item_type, str):
            try:
                obj_item_type = ItemType[obj_item_type.upper()]
            except (KeyError, AttributeError):
                obj_item_type = None
        elif isinstance(obj_item_type, int):
            try:
                obj_item_type = ItemType(obj_item_type)
            except ValueError:
                obj_item_type = None

        if obj_item_type == ItemType.PORTAL:
            values = list(getattr(obj, "value", [0, 0, 0, 0, 0]))
            while len(values) < 5:
                values.append(0)

            portal_flags = int(values[1] if len(values) > 1 else 0)

            EX_ISDOOR = 1
            EX_CLOSED = 2
            EX_LOCKED = 4
            EX_PICKPROOF = 32

            if not (portal_flags & EX_ISDOOR):
                return {"success": False, "message": "You can't do that."}

            if not (portal_flags & EX_CLOSED):
                return {"success": False, "message": "It's not closed."}

            if int(values[4] if len(values) > 4 else 0) < 0:
                return {"success": False, "message": "It can't be unlocked."}

            if portal_flags & EX_PICKPROOF:
                return {"success": False, "message": "You failed."}

            values[1] = portal_flags & ~EX_LOCKED
            obj.value = values

            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            _send_to_char(caster, f"You pick the lock on {short_descr}.")
            broadcast_room(room, f"{_character_name(caster)} picks the lock on {short_descr}.", exclude=caster)
            check_improve(caster, "pick lock", True, 2)
            return {"success": True, "message": "", "picked_type": "portal"}

        if obj_item_type == ItemType.CONTAINER:
            values = list(getattr(obj, "value", [0, 0, 0, 0, 0]))
            while len(values) < 5:
                values.append(0)

            cont_flags = int(values[1] if len(values) > 1 else 0)

            CONT_CLOSEABLE = int(ContainerFlag.CLOSEABLE)
            CONT_CLOSED = int(ContainerFlag.CLOSED)
            CONT_LOCKED = int(ContainerFlag.LOCKED)
            CONT_PICKPROOF = int(ContainerFlag.PICKPROOF)

            if not (cont_flags & CONT_CLOSED):
                return {"success": False, "message": "It's not closed."}

            if int(values[2] if len(values) > 2 else 0) < 0:
                return {"success": False, "message": "It can't be unlocked."}

            if not (cont_flags & CONT_LOCKED):
                return {"success": False, "message": "It's already unlocked."}

            if cont_flags & CONT_PICKPROOF:
                return {"success": False, "message": "You failed."}

            values[1] = cont_flags & ~CONT_LOCKED
            obj.value = values

            short_descr = getattr(obj, "short_descr", None) or getattr(proto, "short_descr", "it")
            _send_to_char(caster, f"You pick the lock on {short_descr}.")
            broadcast_room(room, f"{_character_name(caster)} picks the lock on {short_descr}.", exclude=caster)
            check_improve(caster, "pick lock", True, 2)
            return {"success": True, "message": "", "picked_type": "container"}

    return {"success": False, "message": "You don't see that here."}


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

            disallowed = int(
                WeaponFlag.FLAMING
                | WeaponFlag.FROST
                | WeaponFlag.VAMPIRIC
                | WeaponFlag.SHARP
                | WeaponFlag.VORPAL
                | WeaponFlag.SHOCKING
            )
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
            affect.spell_name = "poison"
            affect.wear_off_message = "The poison on $p dries up."

            affects = getattr(obj, "affected", None)
            if isinstance(affects, list):
                affects.append(affect)
            else:
                obj.affected = [affect]

            new_flags = weapon_flags | int(WeaponFlag.POISON)
            values[4] = new_flags
            obj.value = values
            obj.weapon_flags = new_flags

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


def portal(caster: Character, target: Character | None = None) -> Object | None:
    """ROM ``spell_portal``: conjure a portal that links to the target's room."""

    if caster is None or target is None:
        raise ValueError("portal requires a target")
    if not isinstance(target, Character):
        raise TypeError("portal target must be a Character")

    current_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)

    def _fail() -> None:
        _send_to_char(caster, "You failed.")

    if current_room is None or target_room is None or target is caster:
        _fail()
        return None

    if not can_see_room(caster, target_room):
        _fail()
        return None

    def _room_flags(room) -> int:
        return _coerce_int(getattr(room, "room_flags", 0))

    target_flags = _room_flags(target_room)
    current_flags = _room_flags(current_room)

    disallowed = (
        int(RoomFlag.ROOM_SAFE)
        | int(RoomFlag.ROOM_PRIVATE)
        | int(RoomFlag.ROOM_SOLITARY)
        | int(RoomFlag.ROOM_NO_RECALL)
    )

    if target_flags & disallowed:
        _fail()
        return None
    if current_flags & int(RoomFlag.ROOM_NO_RECALL):
        _fail()
        return None

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    target_level = max(_coerce_int(getattr(target, "level", 0)), 0)
    if target_level >= level + 3:
        _fail()
        return None

    if is_clan_member(target) and not is_same_clan(caster, target):
        _fail()
        return None

    target_is_npc = bool(getattr(target, "is_npc", True))
    if not target_is_npc and target_level >= LEVEL_HERO:
        _fail()
        return None

    if target_is_npc:
        imm_flags = _coerce_int(getattr(target, "imm_flags", 0))
        if imm_flags & int(ImmFlag.SUMMON):
            _fail()
            return None
        if saves_spell(level, target, int(DamageType.NONE)):
            _fail()
            return None

    held_obj = getattr(caster, "equipment", {}).get("hold") if hasattr(caster, "equipment") else None
    held_type = _resolve_item_type(getattr(held_obj, "item_type", None))
    if held_type is None and getattr(held_obj, "prototype", None) is not None:
        held_type = _resolve_item_type(getattr(held_obj.prototype, "item_type", None))

    if not caster.is_immortal():
        if held_obj is None or held_type is not ItemType.WARP_STONE:
            _send_to_char(caster, "You lack the proper component for this spell.")
            return None

    if held_obj is not None and held_type is ItemType.WARP_STONE:
        stone_name = _object_short_descr(held_obj)
        _send_to_char(caster, f"You draw upon the power of {stone_name}.")
        _send_to_char(caster, "It flares brightly and vanishes!")
        if hasattr(caster, "remove_object"):
            caster.remove_object(held_obj)
        if hasattr(held_obj, "location"):
            held_obj.location = None

    portal_obj = spawn_object(OBJ_VNUM_PORTAL)
    if portal_obj is None:
        _fail()
        return None

    timer = 2 + c_div(level, 25)
    portal_obj.timer = timer

    if not isinstance(portal_obj.value, list):
        portal_obj.value = [0, 0, 0, 0, 0]
    while len(portal_obj.value) <= 3:
        portal_obj.value.append(0)
    portal_obj.value[3] = _coerce_int(getattr(target_room, "vnum", 0))

    current_room.add_object(portal_obj)

    portal_name = _object_short_descr(portal_obj)
    broadcast_room(current_room, f"{portal_name} rises up from the ground.", exclude=caster)
    _send_to_char(caster, f"{portal_name} rises up before you.")

    return portal_obj


def protection_evil(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_protection_evil``: apply AFF_PROTECT_EVIL with save bonus."""

    if caster is None:
        raise ValueError("protection_evil requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("protection_evil requires a target")

    if target.has_affect(AffectFlag.PROTECT_EVIL) or target.has_affect(AffectFlag.PROTECT_GOOD):
        if target is caster:
            _send_to_char(caster, "You are already protected.")
        else:
            _send_to_char(caster, f"{_character_name(target)} is already protected.")
        return False
    if target.has_spell_effect("protection evil") or target.has_spell_effect("protection good"):
        if target is caster:
            _send_to_char(caster, "You are already protected.")
        else:
            _send_to_char(caster, f"{_character_name(target)} is already protected.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="protection evil",
        duration=24,
        level=level,
        saving_throw_mod=-1,
        affect_flag=AffectFlag.PROTECT_EVIL,
        wear_off_message="You feel less protected.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "You feel holy and pure.")
    if target is not caster:
        _send_to_char(caster, f"{_character_name(target)} is protected from evil.")
    return True


def protection_good(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_protection_good``: apply AFF_PROTECT_GOOD with save bonus."""

    if caster is None:
        raise ValueError("protection_good requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("protection_good requires a target")

    if target.has_affect(AffectFlag.PROTECT_GOOD) or target.has_affect(AffectFlag.PROTECT_EVIL):
        if target is caster:
            _send_to_char(caster, "You are already protected.")
        else:
            _send_to_char(caster, f"{_character_name(target)} is already protected.")
        return False
    if target.has_spell_effect("protection good") or target.has_spell_effect("protection evil"):
        if target is caster:
            _send_to_char(caster, "You are already protected.")
        else:
            _send_to_char(caster, f"{_character_name(target)} is already protected.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="protection good",
        duration=24,
        level=level,
        saving_throw_mod=-1,
        affect_flag=AffectFlag.PROTECT_GOOD,
        wear_off_message="You feel less protected.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "You feel aligned with darkness.")
    if target is not caster:
        _send_to_char(caster, f"{_character_name(target)} is protected from good.")
    return True


def ray_of_truth(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_ray_of_truth``: alignment-scaled holy damage with blindness."""

    if caster is None or target is None:
        raise ValueError("ray_of_truth requires a caster and target")
    if not isinstance(target, Character):
        raise TypeError("ray_of_truth target must be a Character")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    victim = target

    if is_evil(caster):
        victim = caster
        _send_to_char(caster, "The energy explodes inside you!")
    else:
        if victim is not caster:
            room = getattr(caster, "room", None)
            if room is not None:
                possessive = _possessive_pronoun(caster)
                broadcast_room(
                    room,
                    f"{_character_name(caster)} raises {possessive} hand, and a blinding ray of light shoots forth!",
                    exclude=caster,
                )
            _send_to_char(caster, "You raise your hand and a blinding ray of light shoots forth!")

    if is_good(victim):
        room = getattr(victim, "room", None)
        if room is not None:
            broadcast_room(
                room,
                f"{_character_name(victim)} seems unharmed by the light.",
                exclude=victim,
            )
        _send_to_char(victim, "The light seems powerless to affect you.")
        return 0

    base_damage = rng_mm.dice(level, 10)
    damage = base_damage
    if saves_spell(level, victim, DamageType.HOLY):
        damage = c_div(damage, 2)

    alignment = int(getattr(victim, "alignment", 0) or 0)
    alignment -= 350
    if alignment < -1000:
        alignment = -1000 + c_div(alignment + 1000, 3)

    scaled = c_div(damage * alignment * alignment, 1_000_000)

    before = int(getattr(victim, "hit", 0) or 0)
    apply_damage(caster, victim, max(0, scaled), DamageType.HOLY, dt="ray of truth")
    after = int(getattr(victim, "hit", 0) or 0)

    blind_level = max(0, c_div(3 * level, 4))
    blindness(SimpleNamespace(level=blind_level), victim)

    return max(0, before - after)


def recall(caster: Character, target: Character | None = None) -> str:
    """ROM do_recall - mirrors src/act_move.c:1563-1628."""
    from mud.advancement import gain_exp
    from mud.combat.engine import stop_fighting
    from mud.utils import rng_mm

    if caster is None:
        raise ValueError("recall requires a caster")

    is_npc = getattr(caster, "is_npc", False)
    act_bits = int(getattr(caster, "act", 0) or 0)
    is_pet = bool(act_bits & int(ActFlag.PET))

    if is_npc and not is_pet:
        return "Only players can recall."

    current_room = getattr(caster, "room", None)
    if current_room is not None:
        caster_name = _character_name(caster)
        broadcast_room(current_room, f"{caster_name} prays for transportation!", exclude=caster)

    location = room_registry.get(ROOM_VNUM_TEMPLE)
    if location is None:
        return "You are completely lost."

    if current_room is location:
        return ""

    room_flags = _get_room_flags(current_room)
    if room_flags & int(RoomFlag.ROOM_NO_RECALL) or caster.has_affect(AffectFlag.CURSE):
        return "Mota has forsaken you."

    victim = getattr(caster, "fighting", None)
    if victim is not None:
        skill_pct = _skill_percent(caster, "recall")
        success_rate = 80 * skill_pct // 100

        if rng_mm.number_percent() < success_rate:
            check_improve(caster, "recall", success=False, multiplier=6)
            caster.wait = max(int(getattr(caster, "wait", 0) or 0), 4)
            return "You failed!."

        has_desc = getattr(caster, "desc", None) is not None
        lose = 25 if has_desc else 50
        gain_exp(caster, -lose)
        check_improve(caster, "recall", success=True, multiplier=4)
        stop_fighting(caster, True)
        result_msg = f"You recall from combat!  You lose {lose} exps."
    else:
        result_msg = ""

    move_points = int(getattr(caster, "move", 0) or 0)
    caster.move = c_div(move_points, 2)

    if current_room is not None:
        caster_name = _character_name(caster)
        broadcast_room(current_room, f"{caster_name} disappears.", exclude=caster)
        current_room.remove_character(caster)

    location.add_character(caster)
    broadcast_room(location, f"{_character_name(caster)} appears in the room.", exclude=caster)

    view = look(caster)
    if view:
        result_msg = f"{result_msg}\n{view}" if result_msg else view

    pet = getattr(caster, "pet", None)
    if pet is not None:
        recall(pet)

    return result_msg


def recharge(
    caster: Character,
    target: Object | ObjectData | None = None,
) -> bool:
    """ROM ``spell_recharge``: restore wand/staff charges with chance rolls."""

    if caster is None or target is None:
        raise ValueError("recharge requires a caster and target object")
    if not isinstance(target, (Object, ObjectData)):
        raise TypeError("recharge target must be an object instance")

    obj = target
    item_type = _resolve_item_type(getattr(obj, "item_type", None))
    if item_type is None and getattr(obj, "prototype", None) is not None:
        item_type = _resolve_item_type(getattr(obj.prototype, "item_type", None))

    if item_type not in (ItemType.WAND, ItemType.STAFF):
        _send_to_char(caster, "That item does not carry charges.")
        return False

    values = list(getattr(obj, "value", []) or [])
    while len(values) <= 3:
        values.append(0)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    spell_level = _coerce_int(values[3])
    if spell_level >= c_div(3 * level, 2):
        _send_to_char(caster, "Your skills are not great enough for that.")
        return False

    stored_max = _coerce_int(values[1])
    if stored_max == 0:
        _send_to_char(caster, "That item has already been recharged once.")
        return False

    current_charges = _coerce_int(values[2])

    chance = 40 + 2 * level
    chance -= spell_level
    diff = stored_max - current_charges
    chance -= diff * diff
    chance = max(c_div(level, 2), chance)

    percent = rng_mm.number_percent()

    short_descr = _object_short_descr(obj)
    room = getattr(caster, "room", None)

    if percent < c_div(chance, 2):
        _send_to_char(caster, f"{short_descr} glows softly.")
        if room is not None:
            broadcast_room(room, f"{short_descr} glows softly.", exclude=caster)
        values[2] = max(stored_max, current_charges)
        values[1] = 0
        obj.value = values
        return True

    if percent <= chance:
        _send_to_char(caster, f"{short_descr} glows softly.")
        _send_to_char(caster, f"{short_descr} glows softly.")
        chargemax = stored_max - current_charges
        if chargemax > 0:
            chargeback = max(1, c_div(chargemax * percent, 100))
        else:
            chargeback = 0
        values[2] = current_charges + chargeback
        values[1] = 0
        obj.value = values
        return True

    if percent <= min(95, c_div(3 * chance, 2)):
        _send_to_char(caster, "Nothing seems to happen.")
        if stored_max > 1:
            values[1] = stored_max - 1
            obj.value = values
        return False

    _send_to_char(caster, f"{short_descr} glows brightly and explodes!")
    if room is not None:
        broadcast_room(room, f"{short_descr} glows brightly and explodes!", exclude=caster)
    _extract_runtime_object(obj)
    return False


def refresh(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_refresh``: restore movement points with messaging."""

    if caster is None:
        raise ValueError("refresh requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("refresh requires a target")

    try:
        level = max(int(getattr(caster, "level", 0) or 0), 0)
    except (TypeError, ValueError):
        level = 0

    current_move = int(getattr(target, "move", 0) or 0)
    max_move = int(getattr(target, "max_move", 0) or 0)
    refreshed = current_move + level
    if max_move:
        refreshed = min(refreshed, max_move)
    target.move = refreshed

    if not max_move or refreshed >= max_move:
        _send_to_char(target, "You feel fully refreshed!")
    else:
        _send_to_char(target, "You feel less tired.")

    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def remove_curse(
    caster: Character,
    target: Character | Object | ObjectData | None = None,
) -> bool:
    """ROM ``spell_remove_curse`` for objects and characters."""

    if caster is None:
        raise ValueError("remove_curse requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("remove_curse requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    nouncurse = int(ExtraFlag.NOUNCURSE)
    nodrop = int(ExtraFlag.NODROP)
    noremove = int(ExtraFlag.NOREMOVE)

    def _clear_object_flags(obj: Object | ObjectData) -> bool:
        flags = _effective_extra_flags(obj)
        if not (flags & (nodrop | noremove)):
            _send_to_char(caster, f"There doesn't seem to be a curse on {_object_short_descr(obj)}.")
            return False
        if flags & nouncurse:
            _send_to_char(caster, f"The curse on {_object_short_descr(obj)} is beyond your power.")
            return False

        obj_level = _object_level(obj)
        if saves_dispel(level + 2, obj_level, 0):
            _send_to_char(caster, f"The curse on {_object_short_descr(obj)} is beyond your power.")
            return False

        base_flags = _coerce_int(getattr(obj, "extra_flags", 0) or 0)
        base_flags &= ~nodrop
        base_flags &= ~noremove
        obj.extra_flags = base_flags

        message = f"{_object_short_descr(obj)} glows blue."
        _send_to_char(caster, message)
        room = getattr(caster, "room", None)
        if room is not None:
            broadcast_room(room, message, exclude=caster)
        return True

    if isinstance(target, (Object, ObjectData)):
        return _clear_object_flags(target)

    if not isinstance(target, Character):
        raise TypeError("remove_curse target must be Character or Object")

    victim = target
    room = getattr(victim, "room", None)
    removed_any = False

    if check_dispel(level, victim, "curse"):
        _send_to_char(victim, "You feel better.")
        if room is not None:
            broadcast_room(room, f"{_character_name(victim)} looks more relaxed.", exclude=victim)
        removed_any = True

    seen: set[int] = set()
    objects: list[Object | ObjectData] = []
    inventory = getattr(victim, "inventory", None)
    if isinstance(inventory, list):
        objects.extend(obj for obj in inventory if isinstance(obj, (Object, ObjectData)))
    equipment = getattr(victim, "equipment", None)
    if isinstance(equipment, dict):
        objects.extend(obj for obj in equipment.values() if isinstance(obj, (Object, ObjectData)))

    for obj in objects:
        obj_id = id(obj)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        flags = _effective_extra_flags(obj)
        if not (flags & (nodrop | noremove)) or (flags & nouncurse):
            continue
        obj_level = _object_level(obj)
        if saves_dispel(level, obj_level, 0):
            continue

        base_flags = _coerce_int(getattr(obj, "extra_flags", 0) or 0)
        new_flags = base_flags & ~nodrop & ~noremove
        obj.extra_flags = new_flags

        short_descr = _object_short_descr(obj)
        _send_to_char(victim, f"Your {short_descr} glows blue.")
        if room is not None:
            broadcast_room(
                room,
                f"{_character_name(victim)}'s {short_descr} glows blue.",
                exclude=victim,
            )
        removed_any = True

    return removed_any


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


def shocking_grasp(caster: Character, target: Character | None = None) -> int:
    """ROM spell_shocking_grasp damage table with save-for-half.

    Mirroring ROM src/magic.c:4333-4354.
    """
    if target is None:
        raise ValueError("shocking_grasp requires a target")

    # ROM L4337: damage table for shocking grasp
    dam_each = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        20,
        25,
        29,
        33,
        36,
        39,
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
        49,
        49,
        50,
        50,
        51,
        51,
        52,
        52,
        53,
        53,
        54,
        54,
        55,
        55,
        56,
        56,
        57,
        57,
    ]

    # ROM L4347-4348: clamp level to table bounds
    level = max(getattr(caster, "level", 0), 0)
    capped_level = max(0, min(level, len(dam_each) - 1))

    # ROM L4349: dam = number_range(dam_each[level]/2, dam_each[level]*2)
    base = dam_each[capped_level]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    # ROM L4350-4351: save for half damage
    if saves_spell(level, target, DamageType.LIGHTNING):
        damage = c_div(damage, 2)

    # ROM L4352: damage(ch, victim, dam, sn, DAM_LIGHTNING, TRUE)
    # Simplified: directly apply damage
    target.hit -= damage
    update_pos(target)
    return damage


def sleep(
    caster: Character,
    target: Character | None = None,
    *,
    override_level: int | None = None,
) -> bool:
    """ROM ``spell_sleep``: apply AFF_SLEEP via affect_join semantics."""

    if caster is None or target is None:
        raise ValueError("sleep requires a caster and target")

    if target.has_spell_effect("sleep") or target.has_affect(AffectFlag.SLEEP):
        if target is caster:
            _send_to_char(caster, "You are already fast asleep.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already fast asleep.")
        return False

    if getattr(target, "is_npc", False):
        act_flags = _coerce_int(getattr(target, "act", 0))
        if act_flags & int(ActFlag.UNDEAD):
            if target is not caster:
                _send_to_char(caster, f"{_character_name(target)} is immune to sleep.")
            return False

    base_level = override_level if override_level is not None else getattr(caster, "level", 0)
    level = max(_coerce_int(base_level), 0)
    victim_level = _coerce_int(getattr(target, "level", 0))

    if (level + 2) < victim_level:
        return False

    if saves_spell(max(level - 4, 0), target, DamageType.CHARM):
        return False

    effect = SpellEffect(
        name="sleep",
        duration=4 + level,
        level=level,
        affect_flag=AffectFlag.SLEEP,
        wear_off_message="You feel less tired.",
    )
    target.apply_spell_effect(effect)

    if target.position > Position.SLEEPING:
        _send_to_char(target, "You feel very sleepy ..... zzzzzz.")
        room = getattr(target, "room", None)
        if room is not None:
            room.broadcast(f"{_character_name(target)} goes to sleep.", exclude=target)
        target.position = Position.SLEEPING
    else:
        _send_to_char(target, "You feel very sleepy ..... zzzzzz.")

    return True


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


def steal(
    caster: Character,
    target: Character | None = None,
    *,
    item_name: str = "",
    target_name: str = "",
) -> dict[str, any]:
    """ROM do_steal: attempt to steal gold/items from victim.

    Mirroring ROM src/act_obj.c:2161-2330.

    Returns dict with keys: success (bool), stolen (Object|None), gold (int), silver (int), message (str)
    """
    if caster is None:
        return {"success": False, "message": "No caster"}

    if not item_name or not target_name:
        if target is None:
            return {"success": False, "message": "Steal what from whom?"}

    # ROM L2179-2183: find victim
    if target is None:
        return {"success": False, "message": "They aren't here."}

    # ROM L2185-2189: can't steal from self
    if target is caster:
        return {"success": False, "message": "That's pointless."}

    # ROM L2191-2192: safety check (simplified - no is_safe implemented yet)
    # ROM L2194-2199: can't steal from fighting mob
    if getattr(target, "is_npc", True) and getattr(target, "position", Position.STANDING) == Position.FIGHTING:
        return {"success": False, "message": "Kill stealing is not permitted.\\nYou'd better not -- you might get hit."}

    # ROM L2201-2209: calculate success chance
    percent = rng_mm.number_percent()
    victim_awake = getattr(target, "position", Position.STANDING) > Position.SLEEPING

    if not victim_awake:
        percent -= 10  # ROM L2204-2205: sleeping victim
    # ROM L2206-2209: visibility modifiers (simplified - no can_see check)
    else:
        percent += 50  # ROM L2208: normal penalty

    # ROM L2211-2214: skill check and level range check
    caster_level = int(getattr(caster, "level", 0) or 0)
    target_level = int(getattr(target, "level", 0) or 0)
    caster_skill = int(getattr(caster, "skills", {}).get("steal", 0))
    caster_is_npc = getattr(caster, "is_npc", True)
    target_is_npc = getattr(target, "is_npc", True)

    level_diff_too_high = abs(caster_level - target_level) > 7 and not target_is_npc and not caster_is_npc
    skill_failed = not caster_is_npc and percent > caster_skill

    if level_diff_too_high or skill_failed:
        # ROM L2216-2265: Failure
        caster_name = getattr(caster, "name", "someone")

        # ROM L2220-2221: remove sneak
        if hasattr(caster, "affected_by"):
            caster.affected_by &= ~int(AffectFlag.SNEAK)

        # ROM L2225-2240: yell messages (simplified)
        messages = [
            f"{caster_name} is a lousy thief!",
            f"{caster_name} couldn't rob their way out of a paper bag!",
            f"{caster_name} tried to rob me!",
            f"Keep your hands out of there, {caster_name}!",
        ]
        yell_msg = messages[rng_mm.number_range(0, 3)]

        # ROM L2247-2250: NPC attacks on failure
        result = {
            "success": False,
            "message": "Oops.",
            "victim_yell": yell_msg,
            "victim_attacks": target_is_npc,
        }

        # ROM L2256-2261: Set THIEF flag for PC->PC theft
        if not caster_is_npc and not target_is_npc:
            result["thief_flag"] = True

        return result

    # ROM L2268-2296: Steal gold/coins
    if item_name.lower() in ["coin", "coins", "gold", "silver"]:
        target_gold = int(getattr(target, "gold", 0) or 0)
        target_silver = int(getattr(target, "silver", 0) or 0)
        max_level = 60  # ROM MAX_LEVEL

        # ROM L2274-2275: proportional to level
        gold_stolen = c_div(target_gold * rng_mm.number_range(1, caster_level), max_level)
        silver_stolen = c_div(target_silver * rng_mm.number_range(1, caster_level), max_level)

        if gold_stolen <= 0 and silver_stolen <= 0:
            return {"success": False, "message": "You couldn't get any coins."}

        # ROM L2282-2285: transfer coins
        if hasattr(caster, "gold"):
            caster.gold = getattr(caster, "gold", 0) + gold_stolen
        if hasattr(caster, "silver"):
            caster.silver = getattr(caster, "silver", 0) + silver_stolen
        if hasattr(target, "gold"):
            target.gold -= gold_stolen
        if hasattr(target, "silver"):
            target.silver -= silver_stolen

        # ROM L2286-2294: success message
        if silver_stolen <= 0:
            msg = f"Bingo!  You got {gold_stolen} gold coins."
        elif gold_stolen <= 0:
            msg = f"Bingo!  You got {silver_stolen} silver coins."
        else:
            msg = f"Bingo!  You got {silver_stolen} silver and {gold_stolen} gold coins."

        return {"success": True, "gold": gold_stolen, "silver": silver_stolen, "message": msg}

    # ROM L2299-2311: Steal object (simplified - no object handling yet)
    return {"success": False, "message": "You can't find it."}


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
    disallowed = (
        int(RoomFlag.ROOM_SAFE)
        | int(RoomFlag.ROOM_PRIVATE)
        | int(RoomFlag.ROOM_SOLITARY)
        | int(RoomFlag.ROOM_NO_RECALL)
    )
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


# Passive skill handlers (no command - checked automatically during combat/other actions)


def axe(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Axe is a passive combat skill."}


def dagger(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Dagger is a passive combat skill."}


def dodge(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive defense skill - checked during combat."""
    return {"success": False, "message": "Dodge is a passive defense skill."}


def enhanced_damage(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive damage bonus - applied during combat."""
    return {"success": False, "message": "Enhanced damage is a passive combat bonus."}


def fast_healing(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive regeneration - applied during ticks."""
    return {"success": False, "message": "Fast healing is a passive regeneration skill."}


def flail(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Flail is a passive combat skill."}


def hand_to_hand(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive unarmed combat skill - checked during combat."""
    return {"success": False, "message": "Hand to hand is a passive combat skill."}


def mace(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Mace is a passive combat skill."}


def parry(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive defense skill - checked during combat."""
    return {"success": False, "message": "Parry is a passive defense skill."}


def polearm(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Polearm is a passive combat skill."}


def second_attack(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive multi-attack skill - checked during combat."""
    return {"success": False, "message": "Second attack is a passive combat skill."}


def shield_block(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive defense skill - checked during combat."""
    return {"success": False, "message": "Shield block is a passive defense skill."}


def spear(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Spear is a passive combat skill."}


def sword(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Sword is a passive combat skill."}


def third_attack(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive multi-attack skill - checked during combat."""
    return {"success": False, "message": "Third attack is a passive combat skill."}


def whip(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive weapon proficiency - checked during combat."""
    return {"success": False, "message": "Whip is a passive combat skill."}


def meditation(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Passive mana regeneration skill - applied during ticks."""
    return {"success": False, "message": "Meditation is a passive mana regeneration skill."}


def scrolls(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Magic item usage - invoked via recite command."""
    return {"success": False, "message": "Use the recite command to read scrolls."}


def staves(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Magic item usage - invoked via brandish command."""
    return {"success": False, "message": "Use the brandish command to use staves."}


def wands(caster: Character, target: Character | None = None) -> dict[str, Any]:
    """Magic item usage - invoked via zap command."""
    return {"success": False, "message": "Use the zap command to use wands."}
