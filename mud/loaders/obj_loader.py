from enum import IntFlag
import shlex

from mud.models.constants import (
    AffectFlag,
    ContainerFlag,
    ExtraFlag,
    ImmFlag,
    ItemType,
    LIQUID_TABLE,
    ResFlag,
    VulnFlag,
    WearFlag,
    WeaponFlag,
    WeaponType,
    attack_lookup,
    convert_flags_from_letters,
)
from mud.models.obj import Affect, ObjIndex
from mud.registry import obj_registry
from mud.skills.metadata import ROM_SKILL_NAMES_BY_INDEX

from .base_loader import BaseTokenizer


_CONDITION_MAP = {
    "P": 100,
    "G": 90,
    "A": 75,
    "W": 50,
    "D": 25,
    "B": 10,
    "R": 0,
}


_TO_AFFECTS = 0
_TO_OBJECT = 1
_TO_IMMUNE = 2
_TO_RESIST = 3
_TO_VULN = 4


_ITEM_TYPE_LOOKUP: dict[str, int] = {
    "light": int(ItemType.LIGHT),
    "scroll": int(ItemType.SCROLL),
    "wand": int(ItemType.WAND),
    "staff": int(ItemType.STAFF),
    "weapon": int(ItemType.WEAPON),
    "treasure": int(ItemType.TREASURE),
    "armor": int(ItemType.ARMOR),
    "potion": int(ItemType.POTION),
    "clothing": int(ItemType.CLOTHING),
    "furniture": int(ItemType.FURNITURE),
    "trash": int(ItemType.TRASH),
    "container": int(ItemType.CONTAINER),
    "drink": int(ItemType.DRINK_CON),
    "drink_con": int(ItemType.DRINK_CON),
    "key": int(ItemType.KEY),
    "food": int(ItemType.FOOD),
    "money": int(ItemType.MONEY),
    "boat": int(ItemType.BOAT),
    "npc_corpse": int(ItemType.CORPSE_NPC),
    "pc_corpse": int(ItemType.CORPSE_PC),
    "fountain": int(ItemType.FOUNTAIN),
    "pill": int(ItemType.PILL),
    "protect": int(ItemType.PROTECT),
    "map": int(ItemType.MAP),
    "portal": int(ItemType.PORTAL),
    "warp_stone": int(ItemType.WARP_STONE),
    "room_key": int(ItemType.ROOM_KEY),
    "gem": int(ItemType.GEM),
    "jewelry": int(ItemType.JEWELRY),
    "jukebox": int(ItemType.JUKEBOX),
}


_WEAPON_TYPE_LOOKUP: dict[str, WeaponType] = {
    "exotic": WeaponType.EXOTIC,
    "sword": WeaponType.SWORD,
    "mace": WeaponType.MACE,
    "dagger": WeaponType.DAGGER,
    "axe": WeaponType.AXE,
    "staff": WeaponType.SPEAR,
    "spear": WeaponType.SPEAR,
    "flail": WeaponType.FLAIL,
    "whip": WeaponType.WHIP,
    "polearm": WeaponType.POLEARM,
}


_SKILL_NAMES_LOWER: tuple[str, ...] = tuple(
    name.lower() if isinstance(name, str) else "" for name in ROM_SKILL_NAMES_BY_INDEX
)


def _resolve_item_type_code(token: str | None) -> int:
    if token is None:
        return int(ItemType.TRASH)
    stripped = token.strip()
    if not stripped:
        return int(ItemType.TRASH)
    numeric = stripped.lstrip("-")
    if numeric.isdigit():
        try:
            return int(stripped)
        except ValueError:
            return int(ItemType.TRASH)
    lowered = stripped.lower()
    mapped = _ITEM_TYPE_LOOKUP.get(lowered)
    if mapped is not None:
        return mapped
    normalized = lowered.replace(" ", "_")
    mapped = _ITEM_TYPE_LOOKUP.get(normalized)
    if mapped is not None:
        return mapped
    return int(ItemType.TRASH)


def _weapon_type_lookup(token: str | None) -> int:
    if token is None:
        return int(WeaponType.EXOTIC)
    stripped = token.strip()
    if not stripped:
        return int(WeaponType.EXOTIC)
    numeric = stripped.lstrip("-")
    if numeric.isdigit():
        try:
            return int(stripped)
        except ValueError:
            return int(WeaponType.EXOTIC)
    lowered = stripped.lower()
    mapped = _WEAPON_TYPE_LOOKUP.get(lowered)
    if mapped is not None:
        return int(mapped)
    return int(WeaponType.EXOTIC)


def _liq_lookup(token: str | None) -> int:
    if token is None:
        return 0
    stripped = token.strip()
    if not stripped:
        return 0
    numeric = stripped.lstrip("-")
    if numeric.isdigit():
        try:
            value = int(stripped)
        except ValueError:
            return 0
        if 0 <= value < len(LIQUID_TABLE):
            return value
        return 0
    lowered = stripped.lower()
    for idx, liquid in enumerate(LIQUID_TABLE):
        name = getattr(liquid, "name", "")
        if not name:
            continue
        lowered_name = name.lower()
        if lowered[0] == lowered_name[0] and lowered_name.startswith(lowered):
            return idx
    return 0


def _skill_lookup(token: str | None) -> int:
    if token is None:
        return 0
    stripped = token.strip()
    if not stripped:
        return 0
    numeric = stripped.lstrip("-")
    if numeric.isdigit():
        try:
            value = int(stripped)
        except ValueError:
            return 0
        if 0 <= value < len(_SKILL_NAMES_LOWER):
            return value
        return 0
    lowered = stripped.lower()
    for idx, name in enumerate(_SKILL_NAMES_LOWER):
        if not name:
            continue
        if lowered[0] == name[0] and name.startswith(lowered):
            return idx
    return 0


def _parse_generic_flag(token: str | None) -> int:
    if token is None:
        return 0
    stripped = token.strip().replace("'", "").replace('"', "")
    if not stripped:
        return 0
    total = 0
    for chunk in stripped.split("|"):
        segment = chunk.strip()
        if not segment:
            continue
        negative = False
        if segment.startswith("-"):
            negative = True
            segment = segment[1:].strip()
        value = 0
        idx = 0
        while idx < len(segment) and segment[idx].isalpha():
            ch = segment[idx]
            if "A" <= ch <= "Z":
                value += 1 << (ord(ch) - ord("A"))
            elif "a" <= ch <= "z":
                value += 1 << (ord(ch) - ord("a") + 26)
            idx += 1
        while idx < len(segment) and segment[idx].isdigit():
            value = value * 10 + (ord(segment[idx]) - ord("0"))
            idx += 1
        if negative:
            value = -value
        total |= value
    return total


def _parse_item_values(item_type_code: int, tokens: list[str]) -> list[int]:
    values = [0, 0, 0, 0, 0]
    try:
        item_type = ItemType(item_type_code)
    except ValueError:
        item_type = None

    def token_at(index: int) -> str | None:
        return tokens[index] if index < len(tokens) else None

    if item_type == ItemType.WEAPON:
        values[0] = _weapon_type_lookup(token_at(0))
        values[1] = _safe_int(token_at(1))
        values[2] = _safe_int(token_at(2))
        values[3] = attack_lookup(token_at(3) or "")
        values[4] = _parse_flag_field(token_at(4), WeaponFlag)
        return values
    if item_type == ItemType.CONTAINER:
        values[0] = _safe_int(token_at(0))
        values[1] = _parse_flag_field(token_at(1), ContainerFlag)
        values[2] = _safe_int(token_at(2))
        values[3] = _safe_int(token_at(3))
        values[4] = _safe_int(token_at(4))
        return values
    if item_type in (ItemType.DRINK_CON, ItemType.FOUNTAIN):
        values[0] = _safe_int(token_at(0))
        values[1] = _safe_int(token_at(1))
        values[2] = _liq_lookup(token_at(2))
        values[3] = _safe_int(token_at(3))
        values[4] = _safe_int(token_at(4))
        return values
    if item_type in (ItemType.WAND, ItemType.STAFF):
        values[0] = _safe_int(token_at(0))
        values[1] = _safe_int(token_at(1))
        values[2] = _safe_int(token_at(2))
        values[3] = _skill_lookup(token_at(3))
        values[4] = _safe_int(token_at(4))
        return values
    if item_type in (ItemType.POTION, ItemType.PILL, ItemType.SCROLL):
        values[0] = _safe_int(token_at(0))
        for idx in range(1, 5):
            values[idx] = _skill_lookup(token_at(idx))
        return values
    for idx in range(5):
        values[idx] = _parse_generic_flag(token_at(idx))
    return values


def _safe_int(token: str | None, default: int = 0) -> int:
    if token is None:
        return default
    stripped = token.strip()
    if not stripped:
        return default
    try:
        return int(stripped)
    except (TypeError, ValueError):
        return default


def _parse_condition(token: str | None) -> int:
    if token is None:
        return 100
    stripped = token.strip()
    if not stripped:
        return 100
    numeric = stripped.lstrip("-")
    if numeric.isdigit():
        try:
            return int(stripped)
        except ValueError:
            return 100
    return _CONDITION_MAP.get(stripped.upper(), 100)


def _resolve_where(token: str) -> int:
    return {
        "A": _TO_AFFECTS,
        "I": _TO_IMMUNE,
        "R": _TO_RESIST,
        "V": _TO_VULN,
    }.get(token.upper(), _TO_OBJECT)


def _resolve_bitvector_token(token: str, where: int) -> int:
    stripped = token.strip()
    if not stripped:
        return 0
    try:
        return int(stripped, 0)
    except (TypeError, ValueError):
        pass
    upper = stripped.upper()
    if len(upper) == 1 and "A" <= upper <= "Z":
        return 1 << (ord(upper) - ord("A"))
    mapping: dict[int, tuple[type[IntFlag], tuple[str, ...]]] = {
        _TO_AFFECTS: (AffectFlag, ("AFF_",)),
        _TO_IMMUNE: (ImmFlag, ("IMM_",)),
        _TO_RESIST: (ResFlag, ("RES_",)),
        _TO_VULN: (VulnFlag, ("VULN_", "VUL_")),
    }
    enum_info = mapping.get(where)
    if not enum_info:
        return 0
    enum_cls, prefixes = enum_info
    for prefix in prefixes:
        if upper.startswith(prefix):
            upper = upper[len(prefix) :]
            break
    try:
        return int(getattr(enum_cls, upper))
    except AttributeError:
        return 0


def _parse_bitvector(tokens: list[str], where: int) -> int:
    if not tokens:
        return 0
    bits = 0
    expanded = " ".join(tokens).replace("|", " ")
    for chunk in expanded.split():
        bits |= _resolve_bitvector_token(chunk, where)
    return bits


def _parse_flag_field(token: str | None, enum_cls: type[IntFlag]) -> int:
    if not token:
        return 0
    normalized = token.strip()
    if not normalized:
        return 0
    normalized = normalized.replace("|", " ")
    normalized = normalized.replace("'", "")
    normalized = normalized.replace('"', "")
    try:
        return int(normalized, 0)
    except ValueError:
        pass
    letters = "".join(normalized.split())
    if not letters:
        return 0
    try:
        return int(convert_flags_from_letters(letters, enum_cls))
    except Exception:
        return 0


def load_objects(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line.startswith("#"):
            if line == "#0" or line.startswith("#$"):
                break
            vnum = int(line[1:])
            name = tokenizer.next_line().rstrip("~")
            short_descr = tokenizer.next_line().rstrip("~")
            desc = tokenizer.read_string_tilde()
            extra = tokenizer.read_string_tilde()

            type_line = tokenizer.next_line()
            type_flags_line = shlex.split(type_line) if type_line else []
            item_type = type_flags_line[0] if len(type_flags_line) > 0 else "trash"
            extra_flags_token = type_flags_line[1] if len(type_flags_line) > 1 else ""
            wear_flags_token = type_flags_line[2] if len(type_flags_line) > 2 else ""
            extra_flags = _parse_flag_field(extra_flags_token, ExtraFlag)
            wear_flags = _parse_flag_field(wear_flags_token, WearFlag)

            values_line_raw = tokenizer.next_line()
            values_tokens = shlex.split(values_line_raw) if values_line_raw else []
            item_type_code = _resolve_item_type_code(item_type)
            parsed_values = _parse_item_values(item_type_code, values_tokens)

            stats_line_raw = tokenizer.next_line()
            stats_line = shlex.split(stats_line_raw) if stats_line_raw else []
            level = int(stats_line[0]) if len(stats_line) > 0 and stats_line[0].lstrip("-").isdigit() else 0
            weight = int(stats_line[1]) if len(stats_line) > 1 and stats_line[1].lstrip("-").isdigit() else 0
            cost = int(stats_line[2]) if len(stats_line) > 2 and stats_line[2].lstrip("-").isdigit() else 0
            condition_token = stats_line[3] if len(stats_line) > 3 else None
            condition = _parse_condition(condition_token)

            obj = ObjIndex(
                vnum=vnum,
                name=name,
                short_descr=short_descr,
                description=desc,
                material=extra,
                item_type=item_type,
                extra_flags=extra_flags,
                wear_flags=wear_flags,
                level=level,
                value=parsed_values,
                weight=weight,
                cost=cost,
                condition=condition,
                area=area,
                new_format=True,
            )
            obj_registry[vnum] = obj

            while True:
                peek = tokenizer.peek_line()
                if peek is None or peek.startswith("#") or peek == "$":
                    break
                if peek.startswith("E"):
                    tokenizer.next_line()
                    keyword = tokenizer.next_line().rstrip("~")
                    descr = tokenizer.read_string_tilde()
                    obj.extra_descr.append({"keyword": keyword, "description": descr})
                elif peek.startswith("A"):
                    tokenizer.next_line()
                    affect_line = tokenizer.next_line().split()
                    location = _safe_int(affect_line[0]) if len(affect_line) > 0 else 0
                    modifier = _safe_int(affect_line[1]) if len(affect_line) > 1 else 0
                    obj.affects.append({"location": location, "modifier": modifier})
                    obj.affected.append(
                        Affect(
                            where=_TO_OBJECT,
                            type=-1,
                            level=level,
                            duration=-1,
                            location=location,
                            modifier=modifier,
                            bitvector=0,
                        )
                    )
                elif peek.startswith("F"):
                    parts = tokenizer.next_line().split()
                    if len(parts) >= 5:
                        where_token = parts[1]
                        where = _resolve_where(where_token)
                        location = _safe_int(parts[2])
                        modifier = _safe_int(parts[3])
                        bitvector = _parse_bitvector(parts[4:], where)
                        obj.affects.append(
                            {
                                "where": where_token,
                                "location": location,
                                "modifier": modifier,
                                "bitvector": bitvector,
                            }
                        )
                        obj.affected.append(
                            Affect(
                                where=where,
                                type=-1,
                                level=level,
                                duration=-1,
                                location=location,
                                modifier=modifier,
                                bitvector=bitvector,
                            )
                        )
                else:
                    break
        elif line == "$":
            break
