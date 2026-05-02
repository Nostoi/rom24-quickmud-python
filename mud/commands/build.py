from __future__ import annotations

import json
import shlex
from collections import defaultdict
from pathlib import Path

from mud.models.area import Area
from mud.models.character import Character
from mud.models.clans import get_clan, lookup_clan_id
from mud.models.constants import (
    ATTACK_TABLE,
    EX_CLOSED,
    EX_EASY,
    EX_HARD,
    EX_INFURIATING,
    EX_ISDOOR,
    EX_LOCKED,
    EX_NOCLOSE,
    EX_NOLOCK,
    EX_NOPASS,
    EX_PICKPROOF,
    LIQUID_TABLE,
    ActFlag,
    AreaFlag,
    ContainerFlag,
    Direction,
    ExtraFlag,
    FurnitureFlag,
    PortalFlag,
    Position,
    RoomFlag,
    Sector,
    Sex,
    Size,
    WeaponFlag,
    WeaponType,
    WearFlag,
    WearLocation,
    convert_flags_from_letters,
)
from mud.models.object import Object
from mud.models.races import get_race_by_index
from mud.models.room import Exit, ExtraDescr, Room
from mud.models.room_json import ResetJson
from mud.net.session import Session
from mud.olc.editor_state import EditorMode
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.utils.bit import flag_string, flag_value
from mud.utils.text import format_rom_string

_SECTOR_NAMES: dict[int, str] = {
    int(Sector.INSIDE): "inside",
    int(Sector.CITY): "city",
    int(Sector.FIELD): "field",
    int(Sector.FOREST): "forest",
    int(Sector.HILLS): "hills",
    int(Sector.MOUNTAIN): "mountain",
    # mirroring ROM src/tables.c:391-392 sector_flags — display labels
    # are "swim"/"noswim" (not "water_swim"/"water_noswim").
    int(Sector.WATER_SWIM): "swim",
    int(Sector.WATER_NOSWIM): "noswim",
    int(Sector.UNUSED): "unused",
    int(Sector.AIR): "air",
    int(Sector.DESERT): "desert",
}

_ROOM_FLAG_DISPLAY: tuple[tuple[int, str], ...] = (
    (int(RoomFlag.ROOM_DARK), "dark"),
    (int(RoomFlag.ROOM_NO_MOB), "no_mob"),
    (int(RoomFlag.ROOM_INDOORS), "indoors"),
    (int(RoomFlag.ROOM_PRIVATE), "private"),
    (int(RoomFlag.ROOM_SAFE), "safe"),
    (int(RoomFlag.ROOM_SOLITARY), "solitary"),
    (int(RoomFlag.ROOM_PET_SHOP), "pet_shop"),
    (int(RoomFlag.ROOM_NO_RECALL), "no_recall"),
    (int(RoomFlag.ROOM_IMP_ONLY), "imp_only"),
    (int(RoomFlag.ROOM_GODS_ONLY), "gods_only"),
    (int(RoomFlag.ROOM_HEROES_ONLY), "heroes_only"),
    (int(RoomFlag.ROOM_NEWBIES_ONLY), "newbies_only"),
    (int(RoomFlag.ROOM_LAW), "law"),
    (int(RoomFlag.ROOM_NOWHERE), "nowhere"),
)

_EXIT_FLAG_DISPLAY: tuple[tuple[int, str], ...] = (
    (EX_ISDOOR, "door"),
    (EX_CLOSED, "closed"),
    (EX_LOCKED, "locked"),
    (EX_PICKPROOF, "pickproof"),
    (EX_NOPASS, "nopass"),
    (EX_EASY, "easy"),
    (EX_HARD, "hard"),
    (EX_INFURIATING, "infuriating"),
    (EX_NOCLOSE, "noclose"),
    (EX_NOLOCK, "nolock"),
)

# mirroring ROM src/tables.c:463-483 wear_flags — labels match ROM verbatim
# (no `wear_` prefix on the body slots; "nosac"/"wearfloat" not "no_sac"/"wear_float").
_WEAR_FLAG_DISPLAY: tuple[tuple[int, str], ...] = (
    (int(WearFlag.TAKE), "take"),
    (int(WearFlag.WEAR_FINGER), "finger"),
    (int(WearFlag.WEAR_NECK), "neck"),
    (int(WearFlag.WEAR_BODY), "body"),
    (int(WearFlag.WEAR_HEAD), "head"),
    (int(WearFlag.WEAR_LEGS), "legs"),
    (int(WearFlag.WEAR_FEET), "feet"),
    (int(WearFlag.WEAR_HANDS), "hands"),
    (int(WearFlag.WEAR_ARMS), "arms"),
    (int(WearFlag.WEAR_SHIELD), "shield"),
    (int(WearFlag.WEAR_ABOUT), "about"),
    (int(WearFlag.WEAR_WAIST), "waist"),
    (int(WearFlag.WEAR_WRIST), "wrist"),
    (int(WearFlag.WIELD), "wield"),
    (int(WearFlag.HOLD), "hold"),
    (int(WearFlag.NO_SAC), "nosac"),
    (int(WearFlag.WEAR_FLOAT), "wearfloat"),
)

# mirroring ROM src/tables.c:434-459 extra_flags. ROM omits bit T (1<<19),
# so Python's ExtraFlag.NOLOCATE is intentionally not displayed.
_EXTRA_FLAG_DISPLAY: tuple[tuple[int, str], ...] = (
    (int(ExtraFlag.GLOW), "glow"),
    (int(ExtraFlag.HUM), "hum"),
    (int(ExtraFlag.DARK), "dark"),
    (int(ExtraFlag.LOCK), "lock"),
    (int(ExtraFlag.EVIL), "evil"),
    (int(ExtraFlag.INVIS), "invis"),
    (int(ExtraFlag.MAGIC), "magic"),
    (int(ExtraFlag.NODROP), "nodrop"),
    (int(ExtraFlag.BLESS), "bless"),
    (int(ExtraFlag.ANTI_GOOD), "antigood"),
    (int(ExtraFlag.ANTI_EVIL), "antievil"),
    (int(ExtraFlag.ANTI_NEUTRAL), "antineutral"),
    (int(ExtraFlag.NOREMOVE), "noremove"),
    (int(ExtraFlag.INVENTORY), "inventory"),
    (int(ExtraFlag.NOPURGE), "nopurge"),
    (int(ExtraFlag.ROT_DEATH), "rotdeath"),
    (int(ExtraFlag.VIS_DEATH), "visdeath"),
    (int(ExtraFlag.NONMETAL), "nonmetal"),
    (int(ExtraFlag.MELT_DROP), "meltdrop"),
    (int(ExtraFlag.HAD_TIMER), "hadtimer"),
    (int(ExtraFlag.SELL_EXTRACT), "sellextract"),
    (int(ExtraFlag.BURN_PROOF), "burnproof"),
    (int(ExtraFlag.NOUNCURSE), "nouncurse"),
)

# mirroring ROM src/merc.h:1205-1231 APPLY_* + src/tables.c:489-516 apply_flags.
# APPLY_SAVES (20) and APPLY_SAVING_PARA (20) collide; ROM's flag_string returns
# the first match in the table, "saves".
_APPLY_NAMES: dict[int, str] = {
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
    14: "move",
    15: "gold",
    16: "experience",
    17: "ac",
    18: "hitroll",
    19: "damroll",
    20: "saves",
    21: "savingrod",
    22: "savingpetri",
    23: "savingbreath",
    24: "savingspell",
    25: "spellaffect",
}

_AEDIT_COMMANDS: tuple[str, ...] = (
    "age",
    "builder",
    "commands",
    "create",
    "filename",
    "name",
    "reset",
    "security",
    "show",
    "vnum",
    "lvnum",
    "uvnum",
    "credits",
    "?",
    "version",
)

_REDIT_COMMANDS: tuple[str, ...] = (
    "commands",
    "create",
    "desc",
    "ed",
    "format",
    "name",
    "show",
    "heal",
    "mana",
    "clan",
    "north",
    "south",
    "east",
    "west",
    "up",
    "down",
    "mreset",
    "oreset",
    "mlist",
    "rlist",
    "olist",
    "mshow",
    "oshow",
    "owner",
    "room",
    "sector",
    "?",
    "version",
)

_OEDIT_COMMANDS: tuple[str, ...] = (
    "addaffect",
    "addapply",
    "commands",
    "cost",
    "create",
    "delaffect",
    "ed",
    "long",
    "name",
    "short",
    "show",
    "v0",
    "v1",
    "v2",
    "v3",
    "v4",
    "weight",
    "extra",
    "wear",
    "type",
    "material",
    "level",
    "condition",
    "?",
    "version",
)

_MEDIT_COMMANDS: tuple[str, ...] = (
    "alignment",
    "commands",
    "create",
    "desc",
    "level",
    "long",
    "name",
    "shop",
    "short",
    "show",
    "spec",
    "sex",
    "act",
    "affect",
    "armor",
    "form",
    "part",
    "imm",
    "res",
    "vuln",
    "material",
    "off",
    "size",
    "hitdice",
    "manadice",
    "damdice",
    "race",
    "position",
    "wealth",
    "hitroll",
    "damtype",
    "group",
    "addmprog",
    "delmprog",
    "?",
    "version",
)

_MPEDIT_COMMANDS: tuple[str, ...] = (
    "commands",
    "create",
    "code",
    "show",
    "list",
    "?",
)

_HEDIT_COMMANDS: tuple[str, ...] = (
    "keyword",
    "text",
    "new",
    "level",
    "delete",
    "list",
    "show",
)

# mirroring ROM src/tables.c weapon_class — names match WeaponType members lowercased.
_WEAPON_CLASS_NAMES: dict[int, str] = {
    int(WeaponType.EXOTIC): "exotic",
    int(WeaponType.SWORD): "sword",
    int(WeaponType.DAGGER): "dagger",
    int(WeaponType.SPEAR): "spear",
    int(WeaponType.MACE): "mace",
    int(WeaponType.AXE): "axe",
    int(WeaponType.FLAIL): "flail",
    int(WeaponType.WHIP): "whip",
    int(WeaponType.POLEARM): "polearm",
}


def _show_olc_cmds(command_names: tuple[str, ...]) -> str:
    # mirroring ROM src/olc.c:153-175 show_olc_cmds — 15 chars, 5 columns.
    output = []
    col = 0
    for name in command_names:
        output.append(f"{name:<15.15}")
        col += 1
        if col % 5 == 0:
            output.append("\n\r")
    if col % 5 != 0:
        output.append("\n\r")
    return "".join(output)


def _get_session(char: Character) -> Session | None:
    desc = getattr(char, "desc", None)
    if isinstance(desc, Session):
        return desc
    return None


def _is_builder(char: Character, area: Area | None) -> bool:
    if area is None:
        return False
    # mirrors ROM IS_BUILDER macro (src/merc.h) — leading `!IS_NPC(ch)`
    # short-circuits NPCs before the security/builders comparison, also
    # mirroring `cmd_asave` `IS_NPC(ch) → sec = 0` (src/olc_save.c:933).
    if getattr(char, "is_npc", False):
        return False
    pcdata = getattr(char, "pcdata", None)
    area_security = int(getattr(area, "security", 0))
    char_security = int(getattr(pcdata, "security", 0)) if pcdata else 0
    if area_security > 0 and char_security >= area_security:
        return True
    builders = (getattr(area, "builders", "") or "").strip()
    if builders and builders.lower() not in {"none"}:
        tokens = {token.lower() for token in builders.replace(",", " ").split()}
        if char.name and char.name.lower() in tokens:
            return True
    return False


def _has_help_security(char: Character) -> bool:
    pcdata = getattr(char, "pcdata", None)
    return int(getattr(pcdata, "security", 0) or 0) >= 9


def _mark_area_changed(room: Room | None) -> None:
    # mirrors ROM AREA_CHANGED protocol (src/olc.c:452-463/:510-521).
    # ROM dispatchers SET_BIT(pArea->area_flags, AREA_CHANGED) when an OLC
    # subcommand handler returns TRUE; Python uses an imperative pattern —
    # each `_interpret_*edit` branch (or its helper) calls this after a
    # successful mutation. Documented divergence per OLC_ACT-014; locked
    # by tests/integration/test_olc_act_014_area_changed_protocol.py.
    if not room:
        return
    area = getattr(room, "area", None)
    if area is not None:
        area.changed = True


def _parse_int(value: str | None, default: int) -> int:
    try:
        if value is None:
            raise ValueError
        return int(value, 10)
    except (TypeError, ValueError):
        return default


def _describe_proto(proto: object, fallback: str = "entry") -> str:
    for attr in ("short_descr", "player_name", "name"):
        value = getattr(proto, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _ensure_session_room(session: Session, room: Room) -> None:
    session.editor = "redit"
    session.editor_mode = EditorMode.ROOM
    session.editor_state = {"room": room}


def _clear_session(session: Session) -> None:
    session.editor = None
    session.editor_mode = EditorMode.NONE
    session.editor_state.clear()


def _collect_flag_names(value: int, mapping: tuple[tuple[int, str], ...]) -> list[str]:
    if not value:
        return []
    names: list[str] = []
    for bit, label in mapping:
        if value & bit:
            names.append(label)
    return names


def _format_room_flags(flags: int) -> str:
    tokens = _collect_flag_names(flags, _ROOM_FLAG_DISPLAY)
    return " ".join(tokens) if tokens else "none"


def _format_exit_flags(exit_info: int) -> str:
    tokens = _collect_flag_names(exit_info, _EXIT_FLAG_DISPLAY)
    return " ".join(tokens) if tokens else "none"


def _format_exit_flags_for_show(exit_info: int, reset_flags: int) -> str:
    if not exit_info:
        return "none"
    reset_names = set(_collect_flag_names(reset_flags, _EXIT_FLAG_DISPLAY))
    tokens: list[str] = []
    for bit, label in _EXIT_FLAG_DISPLAY:
        if exit_info & bit:
            tokens.append(label if label in reset_names else label.upper())
    return " ".join(tokens) if tokens else "none"


def _sector_label(sector: int) -> str:
    return _SECTOR_NAMES.get(int(sector), "inside")


def _first_word(text: str | None) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    for token in stripped.split():
        if token:
            return token
    return None


def _collect_character_names(room: Room) -> list[str]:
    names: list[str] = []
    for entity in getattr(room, "people", []) or []:
        proto = getattr(entity, "prototype", None)
        word = _first_word(getattr(entity, "name", None))
        if not word and proto is not None:
            word = _first_word(getattr(proto, "player_name", None))
            if not word:
                word = _first_word(getattr(proto, "short_descr", None))
        if word:
            names.append(word)
    return names


def _collect_object_names(room: Room) -> list[str]:
    names: list[str] = []
    for obj in getattr(room, "contents", []) or []:
        word = _first_word(getattr(obj, "name", None))
        if not word:
            proto = getattr(obj, "prototype", None)
            if proto is not None:
                word = _first_word(getattr(proto, "name", None))
                if not word:
                    word = _first_word(getattr(proto, "short_descr", None))
        if not word:
            word = _first_word(getattr(obj, "short_descr", None))
        if word:
            names.append(word)
    return names


def _room_summary(room: Room) -> str:
    area = getattr(room, "area", None)
    area_vnum = int(getattr(area, "vnum", 0) or 0)
    area_name = (getattr(area, "name", None) or "(no area)").strip() or "(no area)"
    name = (room.name or "(no name)").strip() or "(no name)"
    description = room.description or "(no description set)"
    lines = [
        f"Description:\n{description}",
        f"Name:       [{name}]",
        f"Area:       [{area_vnum:5}] {area_name}",
        f"Vnum:       [{room.vnum:5}]",
        f"Sector:     [{_sector_label(int(getattr(room, 'sector_type', 0)))}]",
        f"Room flags: [{_format_room_flags(int(getattr(room, 'room_flags', 0)))}]",
    ]

    heal_rate = int(getattr(room, "heal_rate", 100))
    mana_rate = int(getattr(room, "mana_rate", 100))
    if heal_rate != 100 or mana_rate != 100:
        lines.append(f"Health rec: [{heal_rate}]")
        lines.append(f"Mana rec  : [{mana_rate}]")

    clan_id = int(getattr(room, "clan", 0) or 0)
    if clan_id > 0:
        clan = get_clan(clan_id)
        clan_name = getattr(clan, "name", "") or ""
        lines.append(f"Clan      : [{clan_id}] {clan_name}")

    owner = (getattr(room, "owner", "") or "").strip()
    if owner:
        lines.append(f"Owner     : [{owner}]")

    extra_keywords = [extra.keyword for extra in room.extra_descr if getattr(extra, "keyword", None)]
    if extra_keywords:
        extras = " ".join(extra_keywords)
        lines.append(f"Desc Kwds:  [{extras}]")

    character_names = _collect_character_names(room)
    if character_names:
        lines.append(f"Characters: [{' '.join(character_names)}]")
    else:
        lines.append("Characters: [none]")

    object_names = _collect_object_names(room)
    if object_names:
        lines.append(f"Objects:    [{' '.join(object_names)}]")
    else:
        lines.append("Objects:    [none]")

    for idx, exit_obj in enumerate(room.exits):
        if not exit_obj:
            continue
        try:
            direction = Direction(idx)
        except ValueError:  # pragma: no cover - defensive guard for malformed exits
            continue
        target_room = getattr(exit_obj, "to_room", None)
        target_vnum = exit_obj.vnum if exit_obj.vnum is not None else getattr(target_room, "vnum", 0) or 0
        key = int(getattr(exit_obj, "key", 0) or 0)
        exit_info = int(getattr(exit_obj, "exit_info", 0) or 0)
        reset_info = int(getattr(exit_obj, "rs_flags", 0) or 0)
        # mirroring ROM src/olc_act.c:1184-1196 redit_show — the first
        # sprintf ends with "Key: [%5d] " (trailing space) and ROM then
        # strcat()s " Exit flags: [", producing two spaces between the
        # closing ']' and "Exit flags".
        lines.append(
            f"-{direction.name.capitalize():<5} to [{target_vnum:5}] Key: [{key:5}]  "
            f"Exit flags: [{_format_exit_flags_for_show(exit_info, reset_info)}]"
        )
        keyword = getattr(exit_obj, "keyword", None)
        if keyword:
            lines.append(f"Kwds: [{keyword}]")
        description_text = getattr(exit_obj, "description", None)
        if description_text:
            lines.append(description_text.rstrip("\n"))

    return "\n".join(lines)


_DIRECTION_ALIASES: dict[str, Direction] = {
    "north": Direction.NORTH,
    "n": Direction.NORTH,
    "east": Direction.EAST,
    "e": Direction.EAST,
    "south": Direction.SOUTH,
    "s": Direction.SOUTH,
    "west": Direction.WEST,
    "w": Direction.WEST,
    "up": Direction.UP,
    "u": Direction.UP,
    "down": Direction.DOWN,
    "d": Direction.DOWN,
}


def _match_token(token: str, *candidates: object) -> bool:
    token = token.lower()
    if not token:
        return False
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            for part in candidate.lower().split():
                if part.startswith(token) or token in part:
                    return True
    return False


def _find_object_in_room(room: Room, token: str) -> Object | None:
    for obj in getattr(room, "contents", []) or []:
        proto = getattr(obj, "prototype", None)
        proto_name = getattr(proto, "name", None) if proto else None
        proto_short = getattr(proto, "short_descr", None) if proto else None
        if _match_token(token, proto_name, proto_short, getattr(obj, "name", None), getattr(obj, "short_descr", None)):
            return obj
    return None


def _find_mob_in_room(room: Room, token: str):
    for entity in getattr(room, "people", []) or []:
        proto = getattr(entity, "prototype", None)
        proto_name = getattr(proto, "player_name", None) if proto else None
        proto_short = getattr(proto, "short_descr", None) if proto else None
        if _match_token(token, getattr(entity, "name", None), proto_name, proto_short):
            return entity
    return None


_WEAR_LOC_ALIASES: dict[str, int] = {
    "none": int(WearLocation.NONE),
    "inventory": int(WearLocation.NONE),
    "light": int(WearLocation.LIGHT),
    "lfinger": int(WearLocation.FINGER_L),
    "rfinger": int(WearLocation.FINGER_R),
    "neck1": int(WearLocation.NECK_1),
    "neck2": int(WearLocation.NECK_2),
    "body": int(WearLocation.BODY),
    "head": int(WearLocation.HEAD),
    "legs": int(WearLocation.LEGS),
    "feet": int(WearLocation.FEET),
    "hands": int(WearLocation.HANDS),
    "arms": int(WearLocation.ARMS),
    "shield": int(WearLocation.SHIELD),
    "about": int(WearLocation.ABOUT),
    "waist": int(WearLocation.WAIST),
    "lwrist": int(WearLocation.WRIST_L),
    "rwrist": int(WearLocation.WRIST_R),
    "wrist": int(WearLocation.WRIST_L),
    "wield": int(WearLocation.WIELD),
    "wielded": int(WearLocation.WIELD),
    "hold": int(WearLocation.HOLD),
    "floating": int(WearLocation.FLOAT),
    "float": int(WearLocation.FLOAT),
}


_WEAR_LOCATION_FLAGS: dict[int, int] = {
    int(WearLocation.NONE): int(WearFlag.TAKE),
    int(WearLocation.LIGHT): int(WearFlag.TAKE),
    int(WearLocation.FINGER_L): int(WearFlag.WEAR_FINGER),
    int(WearLocation.FINGER_R): int(WearFlag.WEAR_FINGER),
    int(WearLocation.NECK_1): int(WearFlag.WEAR_NECK),
    int(WearLocation.NECK_2): int(WearFlag.WEAR_NECK),
    int(WearLocation.BODY): int(WearFlag.WEAR_BODY),
    int(WearLocation.HEAD): int(WearFlag.WEAR_HEAD),
    int(WearLocation.LEGS): int(WearFlag.WEAR_LEGS),
    int(WearLocation.FEET): int(WearFlag.WEAR_FEET),
    int(WearLocation.HANDS): int(WearFlag.WEAR_HANDS),
    int(WearLocation.ARMS): int(WearFlag.WEAR_ARMS),
    int(WearLocation.SHIELD): int(WearFlag.WEAR_SHIELD),
    int(WearLocation.ABOUT): int(WearFlag.WEAR_ABOUT),
    int(WearLocation.WAIST): int(WearFlag.WEAR_WAIST),
    int(WearLocation.WRIST_L): int(WearFlag.WEAR_WRIST),
    int(WearLocation.WRIST_R): int(WearFlag.WEAR_WRIST),
    int(WearLocation.WIELD): int(WearFlag.WIELD),
    int(WearLocation.HOLD): int(WearFlag.HOLD),
    int(WearLocation.FLOAT): int(WearFlag.WEAR_FLOAT),
}


def _resolve_wear_loc(token: str) -> int | None:
    if not token:
        return None
    key = token.strip().lower()
    return _WEAR_LOC_ALIASES.get(key)


def _resolve_wear_flags(proto: object) -> int:
    flags = getattr(proto, "wear_flags", 0)
    if isinstance(flags, WearFlag):
        return int(flags)
    if isinstance(flags, int):
        return flags
    if isinstance(flags, str):
        try:
            return int(convert_flags_from_letters(flags, WearFlag))
        except Exception:
            return 0
    return 0


def _format_wear_flags(flags: int) -> str:
    mapping = [
        ("take", int(WearFlag.TAKE)),
        ("finger", int(WearFlag.WEAR_FINGER)),
        ("neck", int(WearFlag.WEAR_NECK)),
        ("body", int(WearFlag.WEAR_BODY)),
        ("head", int(WearFlag.WEAR_HEAD)),
        ("legs", int(WearFlag.WEAR_LEGS)),
        ("feet", int(WearFlag.WEAR_FEET)),
        ("hands", int(WearFlag.WEAR_HANDS)),
        ("arms", int(WearFlag.WEAR_ARMS)),
        ("shield", int(WearFlag.WEAR_SHIELD)),
        ("about", int(WearFlag.WEAR_ABOUT)),
        ("waist", int(WearFlag.WEAR_WAIST)),
        ("wrist", int(WearFlag.WEAR_WRIST)),
        ("wield", int(WearFlag.WIELD)),
        ("hold", int(WearFlag.HOLD)),
        ("float", int(WearFlag.WEAR_FLOAT)),
    ]
    allowed = [name for name, bit in mapping if flags & bit]
    return " ".join(allowed) if allowed else "none"


def _wear_location_label(wear_loc: int) -> str:
    if wear_loc == int(WearLocation.NONE):
        return "inventory"
    for key, value in _WEAR_LOC_ALIASES.items():
        if value == wear_loc and key not in {"none", "inventory"}:
            return key
    return str(wear_loc)


def _handle_mreset_command(char: Character, room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: mreset <vnum> [max #x] [global #x]"

    vnum_token = args_parts[0]
    try:
        mob_vnum = int(vnum_token, 10)
    except ValueError:
        return "Usage: mreset <vnum> [max #x] [global #x]"

    proto = mob_registry.get(mob_vnum)
    if proto is None:
        return "REdit: No mobile has that vnum."

    room_area = getattr(room, "area", None)
    proto_area = getattr(proto, "area", None)
    if room_area is not None and proto_area is not None and proto_area is not room_area:
        return "REdit: No such mobile in this area."

    per_room_limit = _parse_int(args_parts[1] if len(args_parts) > 1 else None, 1)
    global_limit = _parse_int(args_parts[2] if len(args_parts) > 2 else None, 1)

    spawn = spawn_mob(mob_vnum)
    if spawn is None:
        return "REdit: Unable to create that mobile."

    room.add_mob(spawn)
    reset = ResetJson(command="M", arg1=mob_vnum, arg2=per_room_limit, arg3=room.vnum, arg4=global_limit)
    room.resets.append(reset)
    _mark_area_changed(room)

    name = _describe_proto(proto, "mobile")
    return f"{name} ({mob_vnum}) added to resets with room limit {per_room_limit}."


def _handle_oreset_command(room: Room, args_parts: list[str]) -> str:
    usage = (
        "Usage: oreset <vnum> <args>\n"
        " -no_args               = into room\n"
        " -<obj_name>            = into obj\n"
        " -<mob_name> <wear_loc> = into mob"
    )

    if not args_parts:
        return usage

    try:
        obj_vnum = int(args_parts[0], 10)
    except ValueError:
        return usage

    proto = obj_registry.get(obj_vnum)
    if proto is None:
        return "REdit: No object has that vnum."

    room_area = getattr(room, "area", None)
    proto_area = getattr(proto, "area", None)
    if room_area is not None and proto_area is not None and proto_area is not room_area:
        return "REdit: No such object in this area."

    if len(args_parts) == 1:
        obj = spawn_object(obj_vnum)
        if obj is None:
            return "REdit: Unable to create that object."
        room.add_object(obj)
        room.resets.append(ResetJson(command="O", arg1=obj_vnum, arg2=0, arg3=room.vnum, arg4=0))
        _mark_area_changed(room)
        name = _describe_proto(proto, "object")
        return f"{name} ({obj_vnum}) added to room resets."

    target_token = args_parts[1]
    remaining = args_parts[2:]

    if not remaining:
        container = _find_object_in_room(room, target_token)
        if container is None:
            return "REdit: That container is not in the room."
        obj = spawn_object(obj_vnum)
        if obj is None:
            return "REdit: Unable to create that object."
        obj.cost = 0
        container.contained_items.append(obj)
        container_proto = getattr(container, "prototype", None)
        container_vnum = getattr(container_proto, "vnum", 0)
        room.resets.append(ResetJson(command="P", arg1=obj_vnum, arg2=0, arg3=container_vnum, arg4=1))
        _mark_area_changed(room)
        obj_name = _describe_proto(proto, "object")
        container_name = _describe_proto(container_proto or container, "container")
        return f"{obj_name} ({obj_vnum}) added inside {container_name} ({container_vnum})."

    mob = _find_mob_in_room(room, target_token)
    if mob is None:
        return "REdit: That mobile isn't here."

    wear_loc_token = " ".join(remaining).strip()
    wear_loc = _resolve_wear_loc(wear_loc_token)
    if wear_loc is None:
        return "REdit: Invalid wear_loc. '? wear-loc'"

    required_flag = _WEAR_LOCATION_FLAGS.get(wear_loc, 0)
    wear_flags = _resolve_wear_flags(proto)
    if required_flag and not (wear_flags & required_flag):
        allowed = _format_wear_flags(wear_flags)
        name = _describe_proto(proto, "object")
        return f"{name} wear flags do not allow that slot. Allowed: {allowed}."

    obj = spawn_object(obj_vnum)
    if obj is None:
        return "REdit: Unable to create that object."

    reset_cmd = "G" if wear_loc == int(WearLocation.NONE) else "E"
    obj.wear_loc = wear_loc
    inventory = getattr(mob, "inventory", None)
    if not isinstance(inventory, list):
        inventory = []
        mob.inventory = inventory
    inventory.append(obj)

    if reset_cmd == "E":
        equipment = getattr(mob, "equipment", None)
        if not isinstance(equipment, dict):
            equipment = {}
            mob.equipment = equipment
        equipment[wear_loc] = obj

    room.resets.append(ResetJson(command=reset_cmd, arg1=obj_vnum, arg2=wear_loc, arg3=wear_loc, arg4=0))
    _mark_area_changed(room)

    obj_name = _describe_proto(proto, "object")
    mob_proto = getattr(mob, "prototype", None)
    mob_name = _describe_proto(mob_proto or mob, "mobile")
    mob_vnum = getattr(mob_proto, "vnum", 0) if mob_proto else 0
    slot_label = _wear_location_label(wear_loc)
    return f"{obj_name} ({obj_vnum}) added to {slot_label} of {mob_name} ({mob_vnum})."


_EXIT_FLAG_ALIASES: dict[str, int] = {
    "none": 0,
    "door": EX_ISDOOR,
    "closed": EX_CLOSED,
    "locked": EX_LOCKED,
    "pickproof": EX_PICKPROOF,
    "nopass": EX_NOPASS,
    "easy": EX_EASY,
    "hard": EX_HARD,
    "infuriating": EX_INFURIATING,
    "noclose": EX_NOCLOSE,
    "nolock": EX_NOLOCK,
}

_ROOM_FLAG_ALIASES: dict[str, int] = {
    "dark": int(RoomFlag.ROOM_DARK),
    "no_mob": int(RoomFlag.ROOM_NO_MOB),
    "nomob": int(RoomFlag.ROOM_NO_MOB),
    "indoors": int(RoomFlag.ROOM_INDOORS),
    "private": int(RoomFlag.ROOM_PRIVATE),
    "safe": int(RoomFlag.ROOM_SAFE),
    "solitary": int(RoomFlag.ROOM_SOLITARY),
    "pet_shop": int(RoomFlag.ROOM_PET_SHOP),
    "petshop": int(RoomFlag.ROOM_PET_SHOP),
    "no_recall": int(RoomFlag.ROOM_NO_RECALL),
    "norecall": int(RoomFlag.ROOM_NO_RECALL),
    "imp_only": int(RoomFlag.ROOM_IMP_ONLY),
    "imponly": int(RoomFlag.ROOM_IMP_ONLY),
    "gods_only": int(RoomFlag.ROOM_GODS_ONLY),
    "godsonly": int(RoomFlag.ROOM_GODS_ONLY),
    "heroes_only": int(RoomFlag.ROOM_HEROES_ONLY),
    "heroesonly": int(RoomFlag.ROOM_HEROES_ONLY),
    "newbies_only": int(RoomFlag.ROOM_NEWBIES_ONLY),
    "newbiesonly": int(RoomFlag.ROOM_NEWBIES_ONLY),
    "law": int(RoomFlag.ROOM_LAW),
    "nowhere": int(RoomFlag.ROOM_NOWHERE),
}

_SECTOR_ALIASES: dict[str, int] = {
    "inside": int(Sector.INSIDE),
    "city": int(Sector.CITY),
    "field": int(Sector.FIELD),
    "forest": int(Sector.FOREST),
    "hills": int(Sector.HILLS),
    "mountain": int(Sector.MOUNTAIN),
    "swim": int(Sector.WATER_SWIM),
    "water_swim": int(Sector.WATER_SWIM),
    "noswim": int(Sector.WATER_NOSWIM),
    "water_noswim": int(Sector.WATER_NOSWIM),
    "unused": int(Sector.UNUSED),
    "air": int(Sector.AIR),
    "desert": int(Sector.DESERT),
}


def _ensure_exit(room: Room, direction: Direction) -> Exit:
    if direction.value >= len(room.exits):
        room.exits.extend([None] * (direction.value - len(room.exits) + 1))
    exit_obj = room.exits[direction.value]
    if exit_obj is None:
        exit_obj = Exit()
        room.exits[direction.value] = exit_obj
    return exit_obj


def _handle_exit_command(char: Character, room: Room, direction: Direction, args_parts: list[str]) -> str:
    if not args_parts:
        exit_obj = room.exits[direction.value] if direction.value < len(room.exits) else None
        if exit_obj is None:
            return f"No exit set for {direction.name.lower()}."
        target = exit_obj.vnum if exit_obj.vnum is not None else "(unset)"
        key = exit_obj.key if exit_obj.key else 0
        flags = _format_exit_flags(int(getattr(exit_obj, "exit_info", 0) or 0))
        keyword = exit_obj.keyword or "(none)"
        description = exit_obj.description or "(no description)"
        return (
            f"Exit {direction.name.lower()} -> {target}\nKey: {key} Flags: {flags}\nKeyword: {keyword}\n{description}"
        )

    subcmd = args_parts[0].lower()
    rest = args_parts[1:]
    if subcmd == "create":
        if not rest:
            return "Usage: <direction> create <target vnum>"
        try:
            target_vnum = int(rest[0])
        except ValueError:
            return "Target vnum must be a number."
        exit_obj = _ensure_exit(room, direction)
        exit_obj.vnum = target_vnum
        exit_obj.to_room = room_registry.get(target_vnum)
        exit_obj.exit_info = 0
        exit_obj.key = 0
        exit_obj.keyword = None
        exit_obj.description = None
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} now leads to room {target_vnum}."

    if subcmd in {"delete", "remove"}:
        if direction.value >= len(room.exits) or room.exits[direction.value] is None:
            return "No exit to delete."
        exit_obj = room.exits[direction.value]
        target_room = exit_obj.to_room if isinstance(exit_obj, Exit) else None
        room.exits[direction.value] = None
        _mark_area_changed(room)
        if target_room is not None:
            reverse = _REVERSE_DIRECTIONS.get(direction)
            if reverse is not None and reverse.value < len(target_room.exits):
                target_room.exits[reverse.value] = None
                _mark_area_changed(target_room)
        return f"Exit {direction.name.lower()} removed."

    exit_obj = _ensure_exit(room, direction)

    if subcmd in {"room", "to"}:
        if not rest:
            return "Usage: <direction> room <target vnum>"
        try:
            target_vnum = int(rest[0])
        except ValueError:
            return "Target vnum must be a number."
        exit_obj.vnum = target_vnum
        exit_obj.to_room = room_registry.get(target_vnum)
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} now leads to room {target_vnum}."

    if subcmd == "link":
        if not rest:
            return "Usage: <direction> link <target vnum>"
        try:
            target_vnum = int(rest[0])
        except ValueError:
            return "Target vnum must be a number."
        target_room = room_registry.get(target_vnum)
        if target_room is None:
            return "That room does not exist."
        if not _is_builder(char, getattr(target_room, "area", None)):
            return "You do not have builder rights for that area."
        reverse = _REVERSE_DIRECTIONS.get(direction)
        if reverse is None:
            return "Cannot link exits in that direction."
        if reverse.value < len(target_room.exits) and target_room.exits[reverse.value] is not None:
            return "Remote side's exit already exists."
        exit_obj.vnum = target_vnum
        exit_obj.to_room = target_room
        exit_obj.exit_info = exit_obj.exit_info or 0
        reverse_exit = _ensure_exit(target_room, reverse)
        reverse_exit.vnum = room.vnum
        reverse_exit.to_room = room
        reverse_exit.exit_info = exit_obj.exit_info
        reverse_exit.key = 0
        reverse_exit.keyword = None
        reverse_exit.description = None
        _mark_area_changed(room)
        _mark_area_changed(target_room)
        return "Two-way link established."

    if subcmd == "dig":
        if not rest:
            return "Usage: <direction> dig <room vnum>"
        try:
            new_vnum = int(rest[0])
        except ValueError:
            return "Room vnum must be a number."
        if new_vnum <= 0:
            return "Room vnum must be positive."
        if new_vnum in room_registry:
            target_room = room_registry[new_vnum]
        else:
            area = _get_area_for_vnum(new_vnum)
            if area is None:
                return "That vnum is not assigned to an area."
            if not _is_builder(char, area):
                return "You do not have builder rights for that area."
            target_room = Room(vnum=new_vnum, area=area)
            room_registry[new_vnum] = target_room
            _mark_area_changed(target_room)
        if not _is_builder(char, getattr(target_room, "area", None)):
            return "You do not have builder rights for that area."
        reverse = _REVERSE_DIRECTIONS.get(direction)
        if reverse is None:
            return "Cannot link exits in that direction."
        if reverse.value < len(target_room.exits) and target_room.exits[reverse.value] is not None:
            return "Remote side's exit already exists."
        exit_obj.vnum = target_room.vnum
        exit_obj.to_room = target_room
        reverse_exit = _ensure_exit(target_room, reverse)
        reverse_exit.vnum = room.vnum
        reverse_exit.to_room = room
        reverse_exit.exit_info = exit_obj.exit_info
        _mark_area_changed(room)
        _mark_area_changed(target_room)
        return f"Room {new_vnum} created and linked {direction.name.lower()}."

    if subcmd == "key":
        if not rest:
            return "Usage: <direction> key <object vnum>"
        try:
            key_vnum = int(rest[0])
        except ValueError:
            return "Key must be a number."
        exit_obj.key = key_vnum
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} key set to {key_vnum}."

    if subcmd in {"desc", "description"}:
        if not rest:
            return "Usage: <direction> desc <text>"
        description = " ".join(rest)
        exit_obj.description = description
        _mark_area_changed(room)
        return "Exit description updated."

    if subcmd in {"keyword", "keywords"}:
        if not rest:
            return "Usage: <direction> keyword <text>"
        exit_obj.keyword = " ".join(rest)
        _mark_area_changed(room)
        return "Exit keyword updated."

    if subcmd == "flags":
        if not rest:
            return "Usage: <direction> flags <flag list>"
        if len(rest) == 1 and rest[0].lower() == "none":
            exit_obj.exit_info = 0
            exit_obj.rs_flags = 0
            target_room = exit_obj.to_room
            reverse = _REVERSE_DIRECTIONS.get(direction)
            if target_room is not None and reverse is not None and reverse.value < len(target_room.exits):
                reverse_exit = target_room.exits[reverse.value]
                if isinstance(reverse_exit, Exit):
                    reverse_exit.exit_info = 0
                    reverse_exit.rs_flags = 0
            _mark_area_changed(room)
            return "Exit flags cleared."
        bits = 0
        unknown: defaultdict[str, int] = defaultdict(int)
        for token in rest:
            flag = _EXIT_FLAG_ALIASES.get(token.lower())
            if flag is None:
                unknown[token.lower()] += 1
                continue
            bits |= flag
        if unknown:
            bad = ", ".join(sorted(unknown))
            return f"Unknown exit flags: {bad}."
        exit_obj.exit_info = bits
        exit_obj.rs_flags = bits
        target_room = exit_obj.to_room
        reverse = _REVERSE_DIRECTIONS.get(direction)
        if target_room is not None and reverse is not None and reverse.value < len(target_room.exits):
            reverse_exit = target_room.exits[reverse.value]
            if isinstance(reverse_exit, Exit):
                reverse_exit.exit_info = bits
                reverse_exit.rs_flags = bits
        _mark_area_changed(room)
        return f"Exit flags set to {_format_exit_flags(bits)}."

    return "Unknown exit editor command."


def _find_extra(room: Room, keyword: str) -> ExtraDescr | None:
    for extra in room.extra_descr:
        if (extra.keyword or "").lower() == keyword.lower():
            return extra
    return None


def _handle_extra_command(room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: ed <add|desc|delete|list> ..."
    subcmd = args_parts[0].lower()
    rest = args_parts[1:]
    if subcmd == "list":
        if not room.extra_descr:
            return "No extra descriptions defined."
        lines = ["Extra descriptions:"]
        for extra in room.extra_descr:
            keyword = extra.keyword or "(none)"
            desc = extra.description or "(no description)"
            lines.append(f"- {keyword}: {desc}")
        return "\n".join(lines)

    if subcmd == "add":
        if not rest:
            return "Usage: ed add <keyword>"
        keyword = rest[0]
        extra = _find_extra(room, keyword)
        if extra is None:
            extra = ExtraDescr(keyword=keyword, description="")
            room.extra_descr.append(extra)
        else:
            extra.keyword = keyword
        _mark_area_changed(room)
        return f"Extra description '{keyword}' created. Use 'ed desc {keyword} <text>' to set the text."

    if subcmd in {"delete", "remove"}:
        if not rest:
            return "Usage: ed delete <keyword>"
        keyword = rest[0]
        extra = _find_extra(room, keyword)
        if extra is None:
            return f"No extra description named '{keyword}'."
        room.extra_descr.remove(extra)
        _mark_area_changed(room)
        return f"Extra description '{keyword}' removed."

    if subcmd in {"desc", "description"}:
        if len(rest) < 2:
            return "Usage: ed desc <keyword> <text>"
        keyword = rest[0]
        text = " ".join(rest[1:])
        extra = _find_extra(room, keyword)
        if extra is None:
            extra = ExtraDescr(keyword=keyword)
            room.extra_descr.append(extra)
        extra.description = text
        _mark_area_changed(room)
        return f"Extra description '{keyword}' updated."

    return "Unknown extra description command."


def _handle_room_flags_command(room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: room <flag list>"

    bits = 0
    unknown: defaultdict[str, int] = defaultdict(int)
    for token in args_parts:
        flag = _ROOM_FLAG_ALIASES.get(token.lower())
        if flag is None:
            unknown[token.lower()] += 1
        else:
            bits |= flag

    if unknown:
        bad = ", ".join(sorted(unknown))
        return f"Unknown room flags: {bad}."

    if not bits:
        return "No room flags provided."

    room.room_flags = int(getattr(room, "room_flags", 0)) ^ bits
    _mark_area_changed(room)
    return "Room flags toggled."


def _handle_sector_command(room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: sector <type>"

    token = args_parts[0].lower()
    sector = _SECTOR_ALIASES.get(token)
    if sector is None:
        return f"Unknown sector type: {token}."

    room.sector_type = sector
    _mark_area_changed(room)
    return f"Sector type set to {token}."


def _handle_owner_command(room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: owner <name|none>"

    owner_value = " ".join(args_parts).strip()
    if owner_value.lower() == "none":
        room.owner = ""
    else:
        room.owner = owner_value

    _mark_area_changed(room)
    return "Owner set."


def _interpret_redit(session: Session, char: Character, raw_input: str) -> str:
    room = session.editor_state.get("room") if session.editor_state else None
    if not isinstance(room, Room):
        _clear_session(session)
        return "Room editor session lost. Type '@redit' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: name <value> | desc <value> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid room editor syntax."
    if not parts:
        return "Syntax: name <value> | desc <value> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]
    if cmd == "@redit":
        if not args_parts:
            return "You are already editing this room."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd == "@asave":
        return cmd_asave(char, " ".join(parts[1:]) if len(parts) > 1 else "")

    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting room editor."

    if cmd == "commands":
        return _show_olc_cmds(_REDIT_COMMANDS)

    if cmd == "show":
        return _room_summary(room)

    direction = _DIRECTION_ALIASES.get(cmd)
    if direction is not None:
        return _handle_exit_command(char, room, direction, args_parts)

    if cmd == "ed":
        return _handle_extra_command(room, args_parts)

    if cmd == "room":
        return _handle_room_flags_command(room, args_parts)

    if cmd == "sector":
        return _handle_sector_command(room, args_parts)

    if cmd == "owner":
        return _handle_owner_command(room, args_parts)

    if cmd == "mreset":
        return _handle_mreset_command(char, room, args_parts)

    if cmd == "oreset":
        return _handle_oreset_command(room, args_parts)

    if cmd == "format":
        room.description = format_rom_string(room.description)
        _mark_area_changed(room)
        return "String formatted."

    value = " ".join(args_parts)
    if cmd == "name":
        if not value:
            return "Usage: name <new room name>"
        room.name = value
        _mark_area_changed(room)
        # mirroring ROM src/olc_act.c:1770-1787 redit_name — message verbatim.
        return "Name set."

    if cmd in {"desc", "description"}:
        if not value:
            return "Usage: desc <new room description>"
        room.description = value
        _mark_area_changed(room)
        return "Room description updated."

    if cmd == "heal":
        if not value:
            return "Usage: heal <#xnumber>"
        try:
            heal_rate = int(value, 10)
        except ValueError:
            return "Usage: heal <#xnumber>"
        room.heal_rate = heal_rate
        _mark_area_changed(room)
        return f"Heal rate set to {heal_rate}."

    if cmd == "mana":
        if not value:
            return "Usage: mana <#xnumber>"
        try:
            mana_rate = int(value, 10)
        except ValueError:
            return "Usage: mana <#xnumber>"
        room.mana_rate = mana_rate
        _mark_area_changed(room)
        return f"Mana rate set to {mana_rate}."

    if cmd == "clan":
        if not value:
            return "Usage: clan <name>"
        clan_id = lookup_clan_id(value)
        room.clan = clan_id
        _mark_area_changed(room)
        return f"Room clan set to {clan_id}."

    return "Unknown room editor command."


def cmd_redit(char: Character, args: str) -> str:
    """Room editor entry point — ROM `do_redit` (src/olc.c:745-821)."""
    session = _get_session(char)
    if session is None:
        return "You do not have an active connection to edit from."

    room = getattr(char, "room", None)
    trimmed = args.strip()

    if trimmed and trimmed.lower() in {"done", "exit"}:
        if session.editor == "redit":
            _clear_session(session)
            return "Exiting room editor."
        return "You are not editing any room."

    parts = trimmed.split(None, 1)
    first = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    # mirrors ROM src/olc.c:757-769 — `redit reset`.
    if first == "reset":
        if room is None:
            return "You are nowhere."
        area = getattr(room, "area", None)
        if not _is_builder(char, area):
            return "Insufficient security to modify room.\n\r"
        _apply_resets_for_redit(area)
        if area is not None:
            area.changed = True
        return "Room reset.\n\r"

    # mirrors ROM src/olc.c:770-787 — `redit create <vnum>`.
    if first == "create":
        return _redit_create(session, char, rest)

    # mirrors ROM src/olc.c:789-808 — `redit <vnum>` silent teleport.
    if first.isdigit() or (first.startswith("-") and first[1:].isdigit()):
        return _redit_vnum_teleport(session, char, int(first))

    # Bare or session-already-active path: mirror existing behavior.
    if room is None:
        return "You are nowhere."
    if not _is_builder(char, getattr(room, "area", None)):
        return "You do not have builder rights for this area."

    if session.editor == "redit" and trimmed:
        return _interpret_redit(session, char, trimmed)

    if trimmed:
        _ensure_session_room(session, room)
        return _interpret_redit(session, char, trimmed)

    if session.editor == "redit":
        return "You are already editing this room."

    _ensure_session_room(session, room)
    return "Room editor activated. Type 'show' to review the room and 'done' to exit."


def _apply_resets_for_redit(area: Area | None) -> None:
    """Wrapper around `apply_resets` for `redit reset`.

    ROM `do_redit` calls `reset_room(pRoom)` (src/olc.c:765); Python reuses
    `apply_resets(area)` since no per-room reset helper has been ported yet.
    Documented broader-scope divergence — fully closing it would require
    porting `src/db.c:reset_room`. Indirected through this wrapper so tests
    can monkeypatch it.
    """

    if area is None:
        return
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)


def _redit_create(session: Session, char: Character, argument: str) -> str:
    """Allocate a fresh room and move the builder into it.

    Mirrors ROM `redit_create` (`src/olc_act.c:1716-1766`) and the
    `do_redit` create branch (`src/olc.c:770-787`). Defaults from
    `new_room_index` (`src/mem.c:181-218`): heal_rate=100, mana_rate=100,
    everything else zeroed/empty. After successful create, builder is moved
    into the new room via silent `_char_from_room`/`_char_to_room`.
    """

    arg = argument.strip()
    try:
        vnum = int(arg) if arg else 0
    except ValueError:
        vnum = 0

    # mirrors ROM src/olc.c:772-775 — empty/zero vnum.
    if not arg or vnum <= 0:
        return "Syntax:  edit room create [vnum]\n\r"

    area = _get_area_for_vnum(vnum)
    # mirrors ROM src/olc_act.c:1733-1738.
    if area is None:
        return "REdit:  That vnum is not assigned an area.\n\r"

    # mirrors ROM src/olc_act.c:1740-1744 — IS_BUILDER security gate.
    if not _is_builder(char, area):
        return "REdit:  Vnum in an area you cannot build in.\n\r"

    # mirrors ROM src/olc_act.c:1746-1750.
    if vnum in room_registry:
        return "REdit:  Room vnum already exists.\n\r"

    new_room = Room(vnum=vnum, area=area, heal_rate=100, mana_rate=100)
    room_registry[vnum] = new_room

    # mirrors ROM src/olc.c:781-784 — relocate builder + AREA_CHANGED.
    from mud.commands.imm_commands import _char_from_room, _char_to_room

    if char.room is not None:
        _char_from_room(char)
    _char_to_room(char, new_room)
    area.changed = True

    _ensure_session_room(session, new_room)
    return "Room created.\n\r"


def _redit_vnum_teleport(session: Session, char: Character, vnum: int) -> str:
    """Silently teleport the builder into the target room and start editing.

    Mirrors ROM `do_redit` vnum branch (`src/olc.c:789-808`). Reuses the
    silent primitives `_char_from_room`/`_char_to_room` from imm_commands
    (no `act()` broadcasts) — exactly what ROM does. After the relocate,
    the descriptor's edit pointer is set to the target room.
    """

    target = room_registry.get(vnum)
    # mirrors ROM src/olc.c:793-797.
    if target is None:
        return "REdit : Nonexistant room.\n\r"

    # mirrors ROM src/olc.c:799-804 — IS_BUILDER on TARGET area.
    if not _is_builder(char, getattr(target, "area", None)):
        return "REdit : Insufficient security to modify room.\n\r"

    from mud.commands.imm_commands import _char_from_room, _char_to_room

    if char.room is not None:
        _char_from_room(char)
    _char_to_room(char, target)
    _ensure_session_room(session, target)
    return ""


def handle_redit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_redit(session, char, input_str)


_REVERSE_DIRECTIONS: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}


def _get_area_for_vnum(vnum: int) -> Area | None:
    # mirrors ROM src/olc_act.c:588-599 get_vnum_area — ROM walks the
    # `area_first` linked list; Python iterates `area_registry.values()`.
    # CPython dicts preserve insertion order (3.7+), so load-order traversal
    # is equivalent to ROM's linked-list walk. Locked by
    # tests/integration/test_olc_act_013_get_area_for_vnum_order.py.
    for area in area_registry.values():
        if getattr(area, "min_vnum", 0) <= vnum <= getattr(area, "max_vnum", 0):
            return area
    return None


def cmd_asave(char: Character | None, args: str) -> str:
    # mirrors ROM src/olc_save.c:931-936 — `if (!ch) sec = 9` is the
    # autosave-timer entry: do_asave(NULL, "world") must persist every
    # area regardless of builder. Null-ch path is silent (`if (ch) send_to_char`).
    from mud.olc.save import save_area_list, save_area_to_json

    arg = args.strip().lower()

    if char is None:
        # ROM autosave only ever calls do_asave(NULL, "world"). Other
        # null-ch paths aren't reachable in ROM; return silently rather
        # than crash on later char-attribute access.
        if arg != "world":
            return ""

    if not arg:
        return (
            "Syntax:\n"
            "  asave <vnum>   - saves a particular area\n"
            "  asave list     - saves the area.lst file\n"
            "  asave area     - saves the area being edited\n"
            "  asave changed  - saves all changed zones\n"
            "  asave world    - saves the world! (db dump)\n"
        )

    if arg.isdigit():
        vnum = int(arg)
        area = area_registry.get(vnum)
        if area is None:
            area = _get_area_for_vnum(vnum)
        if area is None:
            return "That area does not exist."

        if not _is_builder(char, area):
            return "You are not a builder for this area."

        save_area_list()
        success = save_area_to_json(area)
        if success:
            return f"Area {area.name} (vnum {area.vnum}) saved."
        else:
            return "Failed to save area."

    if arg == "world":
        # mirrors ROM src/olc_save.c:1000-1018 — autosave (ch=NULL) saves
        # every area, skipping the IS_BUILDER gate; player path keeps it.
        save_area_list()
        saved_count = 0
        for area in area_registry.values():
            if char is not None and not _is_builder(char, area):
                continue
            if save_area_to_json(area):
                saved_count += 1

        if char is None:
            return ""
        return f"You saved the world. ({saved_count} areas)"

    if arg == "changed":
        save_area_list()
        saved_areas: list[str] = []

        for area in area_registry.values():
            if not _is_builder(char, area):
                continue

            if getattr(area, "changed", False):
                if save_area_to_json(area):
                    area_name = getattr(area, "name", "Unknown") or "Unknown"
                    file_name = getattr(area, "file_name", "unknown") or "unknown"
                    saved_areas.append(f"{area_name:24} - '{file_name}'")

        if not saved_areas:
            return "No changed areas to save."

        result = "Saved zones:\n" + "\n".join(saved_areas)
        return result

    if arg == "list":
        success = save_area_list()
        if success:
            return "Area list saved."
        else:
            return "Failed to save area list."

    if arg == "area":
        session = _get_session(char)
        if session is None:
            return "You do not have an active connection."

        # mirroring ROM src/olc_save.c:1085-1115 — dispatch on ch->desc->editor
        # across ED_AREA / ED_ROOM / ED_OBJECT / ED_MOBILE / ED_HELP.
        editor = session.editor
        if editor in (None, "", "none"):
            return "You are not editing an area, therefore an area vnum is required."

        state = session.editor_state or {}
        area: Area | None = None

        if editor == "aedit":
            candidate = state.get("area")
            if isinstance(candidate, Area):
                area = candidate
        elif editor == "redit":
            room = state.get("room")
            if isinstance(room, Room):
                area = getattr(room, "area", None)
        elif editor == "oedit":
            obj_proto = state.get("obj_proto")
            if obj_proto is not None:
                area = getattr(obj_proto, "area", None)
        elif editor == "medit":
            mob_proto = state.get("mob_proto")
            if mob_proto is not None:
                area = getattr(mob_proto, "area", None)
        elif editor == "hedit":
            # mirroring ROM src/olc_save.c:1110-1113 — ED_HELP branch sends
            # "Grabando area : " then save_other_helps(). Help-save port is
            # tracked separately as OLC_SAVE-009.
            return "Grabando area : help save not yet implemented (OLC_SAVE-009)."
        else:
            # Unknown editor — fall through to ROM's default (use ch->in_room->area).
            current_room = getattr(char, "room", None)
            if isinstance(current_room, Room):
                area = getattr(current_room, "area", None)

        if area is None:
            return "You are not editing an area, therefore an area vnum is required."

        if not _is_builder(char, area):
            return "You are not a builder for this area."

        save_area_list()
        success = save_area_to_json(area)
        if success:
            return f"Area {area.name} saved."
        else:
            return "Failed to save area."

    return "Invalid argument. Use 'asave' with no arguments for help."


def cmd_aedit(char: Character, args: str) -> str:
    """Area editor - ROM src/olc.c:410-469."""
    session = _get_session(char)
    if session is None:
        return "You do not have an active connection."

    arg = args.strip()

    if session.editor == "aedit":
        return _interpret_aedit(session, char, arg)

    if arg.lower() == "create":
        # mirrors ROM src/olc.c:222 (aedit_table "create" entry) + src/olc_act.c:667-679
        return _aedit_create(session)

    if not arg:
        return "Syntax: @aedit <area vnum>"

    try:
        area_vnum = int(arg)
    except ValueError:
        return "Area vnum must be a number."

    area = area_registry.get(area_vnum)
    if area is None:
        return "That area does not exist."

    if not _is_builder(char, area):
        return "Insufficient security to edit this area."

    _ensure_session_area(session, area)
    return f"Now editing area {area.name} (vnum {area.vnum}).\nType 'show' to display area info, 'done' to exit."


def _aedit_create(session: Session) -> str:
    """Allocate a fresh area and switch the descriptor's edit target.

    Mirrors ROM `aedit_create` (`src/olc_act.c:667-679`). Defaults come from
    `new_area()` (`src/mem.c:91-122`): name="New area", builders="None",
    security=1, min/max_vnum=0, empty=True, area_flags=AREA_ADDED, file_name
    derived from vnum. ROM uses a global `top_area` counter to assign vnums;
    Python uses `max(area_registry) + 1` since `area_registry` is a dict.
    The redundant `SET_BIT(area_flags, AREA_ADDED)` at src/olc_act.c:676 is
    idempotent — `new_area` already sets it.
    """

    new_vnum = max(area_registry.keys(), default=-1) + 1
    area = Area(
        vnum=new_vnum,
        name="New area",
        builders="None",
        security=1,
        min_vnum=0,
        max_vnum=0,
        age=0,
        nplayer=0,
        empty=True,
        area_flags=int(AreaFlag.ADDED),
        file_name=f"area{new_vnum}.are",
    )
    area_registry[new_vnum] = area
    _ensure_session_area(session, area)
    return "Area Created.\n\r"


def _ensure_session_area(session: Session, area: Area) -> None:
    session.editor = "aedit"
    session.editor_mode = EditorMode.AREA
    session.editor_state = {"area": area}


def _interpret_aedit(session: Session, char: Character, raw_input: str) -> str:
    """Command interpreter for aedit - ROM src/olc.c:216-235 (aedit_table)."""
    area = session.editor_state.get("area") if session.editor_state else None
    if not isinstance(area, Area):
        _clear_session(session)
        return "Area editor session lost. Type '@aedit <vnum>' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: name <value> | credits <value> | security <number> | builder <add|remove> <name> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid area editor syntax."

    if not parts:
        return "Syntax: name <value> | credits <value> | security <number> | builder <add|remove> <name> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]

    if cmd == "@aedit":
        if not args_parts:
            return "You are already editing this area."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd == "@asave":
        return cmd_asave(char, " ".join(parts[1:]) if len(parts) > 1 else "")

    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting area editor."

    # mirroring ROM src/olc.c:443-449 — flag_value(area_flags, command) toggle
    # prefix; checked before aedit_table[] dispatch so builders can type a flag
    # name directly to toggle it (e.g. "loading", "added").
    _flag_val = flag_value(AreaFlag, cmd)
    if _flag_val is not None:
        area.area_flags ^= _flag_val  # TOGGLE_BIT
        area.changed = True
        return "Flag toggled."

    if cmd == "create":
        # mirrors ROM aedit_table dispatch (src/olc.c:222) — `create` typed
        # inside an active aedit session also allocates a new area and
        # switches the descriptor's edit target.
        return _aedit_create(session)

    if cmd == "commands":
        return _show_olc_cmds(_AEDIT_COMMANDS)

    if cmd == "show":
        return _aedit_show(area)

    if cmd == "reset":
        # mirroring ROM src/olc_act.c:653-663 aedit_reset — calls
        # `reset_area(pArea)` and sends "Area reset.\n\r".
        _apply_resets_for_redit(area)
        area.changed = True
        return "Area reset."

    if cmd == "name":
        if not args_parts:
            return "Usage: name <new area name>"
        new_name = " ".join(args_parts)
        area.name = new_name
        area.changed = True
        # mirroring ROM src/olc_act.c:683-700 aedit_name — message verbatim.
        return "Name set."

    if cmd == "credits":
        if not args_parts:
            return "Usage: credits <author name>"
        new_credits = " ".join(args_parts)
        area.credits = new_credits
        area.changed = True
        return f"Area credits set to: {new_credits}"

    if cmd == "security":
        if not args_parts:
            return "Usage: security <0-9>"
        try:
            security_level = int(args_parts[0])
        except ValueError:
            return "Security level must be a number."

        if security_level < 0 or security_level > 9:
            return "Security level must be between 0 and 9."

        area.security = security_level
        area.changed = True
        return f"Security level set to {security_level}."

    if cmd == "builder":
        return _handle_builder_command(area, args_parts)

    if cmd == "vnum":
        if not args_parts:
            return "Usage: vnum <area vnum>"
        try:
            new_vnum = int(args_parts[0])
        except ValueError:
            return "Area vnum must be a number."
        area.vnum = new_vnum
        area.changed = True
        return f"Area vnum set to {new_vnum}."

    if cmd == "lvnum":
        if not args_parts:
            return "Usage: lvnum <lower vnum>"
        try:
            lvnum = int(args_parts[0])
        except ValueError:
            return "Lower vnum must be a number."
        area.min_vnum = lvnum
        area.changed = True
        return f"Lower vnum set to {lvnum}."

    if cmd == "uvnum":
        if not args_parts:
            return "Usage: uvnum <upper vnum>"
        try:
            uvnum = int(args_parts[0])
        except ValueError:
            return "Upper vnum must be a number."
        area.max_vnum = uvnum
        area.changed = True
        return f"Upper vnum set to {uvnum}."

    if cmd == "filename":
        if not args_parts:
            return "Usage: filename <filename>"
        new_filename = args_parts[0]
        area.file_name = new_filename
        area.changed = True
        return f"Filename set to: {new_filename}"

    return f"Unknown area editor command: {cmd}"


def _aedit_show(area: Area) -> str:
    lines = []
    lines.append(f"Area: {area.name or '(unnamed)'}")
    lines.append(f"Vnum:     {area.vnum}")
    lines.append(f"File:     {area.file_name or '(none)'}")
    lines.append(f"Vnums:    {area.min_vnum} - {area.max_vnum}")
    lines.append(f"Security: {area.security}")
    lines.append(f"Builders: {area.builders or 'None'}")
    lines.append(f"Credits:  {area.credits or '(none)'}")
    # mirroring ROM src/olc_act.c:644-646 aedit_show flags row
    lines.append(f"Flags:    [{flag_string(AreaFlag, area.area_flags)}]")
    lines.append(f"Changed:  {'Yes' if area.changed else 'No'}")
    return "\n".join(lines)


def _handle_builder_command(area: Area, args_parts: list[str]) -> str:
    """Builder list management - ROM src/olc.c:builder."""
    if len(args_parts) < 2:
        return "Usage: builder <add|remove> <name>"

    action = args_parts[0].lower()
    builder_name = args_parts[1].lower()

    if action not in {"add", "remove"}:
        return "Usage: builder <add|remove> <name>"

    builders_str = (area.builders or "").strip()
    if builders_str.lower() in {"", "none"}:
        builders_list = []
    else:
        builders_list = [b.strip().lower() for b in builders_str.replace(",", " ").split() if b.strip()]

    if action == "add":
        if builder_name in builders_list:
            return f"Builder '{builder_name}' is already in the list."
        builders_list.append(builder_name)
        area.builders = " ".join(builders_list)
        area.changed = True
        return f"Builder '{builder_name}' added."

    if action == "remove":
        if builder_name not in builders_list:
            return f"Builder '{builder_name}' is not in the list."
        builders_list.remove(builder_name)
        area.builders = " ".join(builders_list) if builders_list else "None"
        area.changed = True
        return f"Builder '{builder_name}' removed."

    return "Unknown builder command."


def handle_aedit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_aedit(session, char, input_str)


def cmd_oedit(char: Character, args: str) -> str:
    """Object editor - ROM src/olc.c:532-584."""
    session = _get_session(char)
    if session is None:
        return "You do not have an active connection."

    arg = args.strip()

    if session.editor == "oedit":
        return _interpret_oedit(session, char, arg)

    # mirrors ROM oedit_table dispatch — `create <vnum>` is its own subcommand,
    # not implicit on every unknown vnum.
    parts = arg.split(None, 1)
    if parts and parts[0].lower() == "create":
        rest = parts[1] if len(parts) > 1 else ""
        return _oedit_create(session, char, rest)

    if not arg:
        return "Syntax: @oedit <object vnum>"

    try:
        obj_vnum = int(arg)
    except ValueError:
        return "Object vnum must be a number."

    from mud.models.obj import obj_index_registry

    obj_proto = obj_index_registry.get(obj_vnum)
    if obj_proto is None:
        # mirrors ROM `do_oedit` — without explicit `create`, an unknown vnum is
        # an error, not an auto-allocate.
        return "That object does not exist. Use 'oedit create <vnum>' to create it."

    area = getattr(obj_proto, "area", None)
    if not _is_builder(char, area):
        return "Insufficient security to edit this object."

    _ensure_session_obj(session, obj_proto)
    return f"Now editing object {obj_proto.short_descr or '(unnamed)'} (vnum {obj_vnum}).\nType 'show' to display, 'done' to exit."


def _oedit_create(session: Session, char: Character, argument: str) -> str:
    """Allocate a fresh object prototype.

    Mirrors ROM `oedit_create` (`src/olc_act.c:3178-3225`). Defaults from
    `new_obj_index` (`src/mem.c:297-335`): name="no name", short_descr=
    "(no short description)", description="(no description)", item_type=
    ITEM_TRASH (Python "trash"), extra_flags=0, wear_flags=0, weight=0,
    cost=0, material="unknown", value=[0]*5, new_format=True. Validation
    chain: vnum required → area assignment → IS_BUILDER → already-exists.
    """

    from mud.models.obj import ObjIndex, obj_index_registry

    arg = argument.strip()
    try:
        vnum = int(arg) if arg else 0
    except ValueError:
        vnum = 0

    # mirrors ROM src/olc_act.c:3186-3190 — empty or zero vnum.
    if not arg or vnum == 0:
        return "Syntax:  oedit create [vnum]\n\r"

    area = _get_area_for_vnum(vnum)
    # mirrors ROM src/olc_act.c:3192-3197 — vnum must belong to an area.
    if area is None:
        return "OEdit:  That vnum is not assigned an area.\n\r"

    # mirrors ROM src/olc_act.c:3199-3203 — IS_BUILDER security gate.
    if not _is_builder(char, area):
        return "OEdit:  Vnum in an area you cannot build in.\n\r"

    # mirrors ROM src/olc_act.c:3205-3209 — already-exists check.
    if vnum in obj_index_registry:
        return "OEdit:  Object vnum already exists.\n\r"

    proto = ObjIndex(
        vnum=vnum,
        area=area,
        name="no name",
        short_descr="(no short description)",
        description="(no description)",
        material="unknown",
        item_type="trash",
        extra_flags=0,
        wear_flags=0,
        weight=0,
        cost=0,
        value=[0, 0, 0, 0, 0],
        new_format=True,
    )
    obj_index_registry[vnum] = proto
    _ensure_session_obj(session, proto)
    return "Object Created.\n\r"


def _ensure_session_obj(session: Session, obj_proto) -> None:
    session.editor = "oedit"
    session.editor_mode = EditorMode.OBJECT
    session.editor_state = {"obj_proto": obj_proto}


def _interpret_oedit(session: Session, char: Character, raw_input: str) -> str:
    """Command interpreter for oedit - ROM src/olc.c:oedit_table."""
    from mud.models.obj import ObjIndex

    obj_proto = session.editor_state.get("obj_proto") if session.editor_state else None
    if not isinstance(obj_proto, ObjIndex):
        _clear_session(session)
        return "Object editor session lost. Type '@oedit <vnum>' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: name <value> | short <value> | long <value> | type <type> | level <num> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid object editor syntax."

    if not parts:
        return "Syntax: name <value> | short <value> | long <value> | type <type> | level <num> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]

    if cmd == "@oedit":
        if not args_parts:
            return "You are already editing this object."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd == "@asave":
        return cmd_asave(char, " ".join(parts[1:]) if len(parts) > 1 else "")

    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting object editor."

    if cmd == "create":
        # mirrors ROM oedit_table dispatch — `create <vnum>` typed inside an
        # active oedit session also allocates and switches the edit target.
        return _oedit_create(session, char, " ".join(args_parts))

    if cmd == "commands":
        return _show_olc_cmds(_OEDIT_COMMANDS)

    if cmd == "show":
        return _oedit_show(obj_proto)

    if cmd == "name":
        if not args_parts:
            return "Usage: name <keywords>"
        new_name = " ".join(args_parts)
        obj_proto.name = new_name
        _mark_obj_changed(obj_proto)
        # mirroring ROM src/olc_act.c:2990-3010 oedit_name — message verbatim.
        return "Name set."

    if cmd == "short":
        if not args_parts:
            return "Usage: short <short description>"
        new_short = " ".join(args_parts)
        obj_proto.short_descr = new_short
        _mark_obj_changed(obj_proto)
        return f"Short description set to: {new_short}"

    if cmd == "long":
        if not args_parts:
            return "Usage: long <long description>"
        new_long = " ".join(args_parts)
        obj_proto.description = new_long
        _mark_obj_changed(obj_proto)
        return f"Long description set to: {new_long}"

    if cmd == "type":
        if not args_parts:
            return "Usage: type <item type>"
        item_type = args_parts[0].lower()
        obj_proto.item_type = item_type
        _mark_obj_changed(obj_proto)
        return f"Item type set to: {item_type}"

    if cmd == "level":
        if not args_parts:
            return "Usage: level <number>"
        try:
            level = int(args_parts[0])
        except ValueError:
            return "Level must be a number."
        if level < 0:
            return "Level must be non-negative."
        obj_proto.level = level
        _mark_obj_changed(obj_proto)
        return f"Object level set to {level}."

    if cmd == "weight":
        if not args_parts:
            return "Usage: weight <number>"
        try:
            weight = int(args_parts[0])
        except ValueError:
            return "Weight must be a number."
        obj_proto.weight = weight
        _mark_obj_changed(obj_proto)
        return f"Weight set to {weight}."

    if cmd == "cost":
        if not args_parts:
            return "Usage: cost <number>"
        try:
            cost = int(args_parts[0])
        except ValueError:
            return "Cost must be a number."
        obj_proto.cost = cost
        _mark_obj_changed(obj_proto)
        return f"Cost set to {cost}."

    if cmd == "material":
        if not args_parts:
            return "Usage: material <name>"
        material = " ".join(args_parts)
        obj_proto.material = material
        _mark_obj_changed(obj_proto)
        return f"Material set to: {material}"

    if cmd in {"v0", "v1", "v2", "v3", "v4"}:
        index = int(cmd[1])
        if not args_parts:
            return f"Usage: {cmd} <number>"
        try:
            value = int(args_parts[0])
        except ValueError:
            return "Value must be a number."
        if not isinstance(obj_proto.value, list):
            obj_proto.value = [0, 0, 0, 0, 0]
        while len(obj_proto.value) <= index:
            obj_proto.value.append(0)
        obj_proto.value[index] = value
        _mark_obj_changed(obj_proto)
        return f"Value[{index}] set to {value}."

    if cmd == "ed":
        return _handle_obj_extra_command(obj_proto, args_parts)

    return f"Unknown object editor command: {cmd}"


def _format_wear_flags(bits: int) -> str:
    tokens = [label for bit, label in _WEAR_FLAG_DISPLAY if bits & bit]
    return " ".join(tokens) if tokens else "none"


def _format_extra_flags(bits: int) -> str:
    tokens = [label for bit, label in _EXTRA_FLAG_DISPLAY if bits & bit]
    return " ".join(tokens) if tokens else "none"


def _format_weapon_special(bits: int) -> str:
    tokens = [m.name.lower() for m in WeaponFlag if bits & int(m)]
    return " ".join(tokens) if tokens else "none"


def _format_container_flags(bits: int) -> str:
    tokens = [m.name.lower() for m in ContainerFlag if bits & int(m)]
    return " ".join(tokens) if tokens else "none"


def _format_furniture_flags(bits: int) -> str:
    tokens = [m.name.lower() for m in FurnitureFlag if bits & int(m)]
    return " ".join(tokens) if tokens else "none"


def _format_portal_flags(bits: int) -> str:
    tokens = [m.name.lower() for m in PortalFlag if bits & int(m)]
    return " ".join(tokens) if tokens else "none"


def _format_exit_flags_raw(bits: int) -> str:
    tokens = [label for bit, label in _EXIT_FLAG_DISPLAY if bits & bit]
    return " ".join(tokens) if tokens else "none"


def _coerce_int(value, default: int = 0) -> int:
    try:
        if isinstance(value, str):
            return int(value, 10)
        return int(value)
    except (TypeError, ValueError):
        return default


def _show_obj_values(obj_proto) -> list[str]:
    """Mirroring ROM src/olc_act.c:2210-2374 show_obj_values — emit
    type-specific value rows. Returns lines (each WITHOUT trailing newline).
    """
    item_type = obj_proto.item_type
    if isinstance(item_type, str):
        kind = item_type.lower()
    else:
        kind = str(item_type).lower()
    values = obj_proto.value if isinstance(obj_proto.value, list) else [0, 0, 0, 0, 0]
    v = [_coerce_int(values[i]) if i < len(values) else 0 for i in range(5)]
    out: list[str] = []

    if kind == "light":
        # ROM olc_act.c:2219-2225
        if v[2] in (-1, 999):
            out.append("[v2] Light:  Infinite[-1]")
        else:
            out.append(f"[v2] Light:  [{v[2]}]")
    elif kind in ("wand", "staff"):
        # ROM olc_act.c:2227-2240 — spell name lookup by index not yet ported;
        # emit raw v[3] index as fallback.
        out.append(f"[v0] Level:          [{v[0]}]")
        out.append(f"[v1] Charges Total:  [{v[1]}]")
        out.append(f"[v2] Charges Left:   [{v[2]}]")
        out.append(f"[v3] Spell:          {'none' if v[3] == -1 else f'[{v[3]}]'}")
    elif kind == "portal":
        # ROM olc_act.c:2242-2253
        out.append(f"[v0] Charges:        [{v[0]}]")
        out.append(f"[v1] Exit Flags:     {_format_exit_flags_raw(v[1])}")
        out.append(f"[v2] Portal Flags:   {_format_portal_flags(v[2])}")
        out.append(f"[v3] Goes to (vnum): [{v[3]}]")
    elif kind == "furniture":
        # ROM olc_act.c:2255-2267
        out.append(f"[v0] Max people:      [{v[0]}]")
        out.append(f"[v1] Max weight:      [{v[1]}]")
        out.append(f"[v2] Furniture Flags: {_format_furniture_flags(v[2])}")
        out.append(f"[v3] Heal bonus:      [{v[3]}]")
        out.append(f"[v4] Mana bonus:      [{v[4]}]")
    elif kind in ("scroll", "potion", "pill"):
        # ROM olc_act.c:2269-2288 — spell-name lookup by index not yet ported.
        out.append(f"[v0] Level:  [{v[0]}]")
        for i in (1, 2, 3, 4):
            out.append(f"[v{i}] Spell:  {'none' if v[i] == -1 else f'[{v[i]}]'}")
    elif kind == "armor":
        # ROM olc_act.c:2292-2301
        out.append(f"[v0] Ac pierce       [{v[0]}]")
        out.append(f"[v1] Ac bash         [{v[1]}]")
        out.append(f"[v2] Ac slash        [{v[2]}]")
        out.append(f"[v3] Ac exotic       [{v[3]}]")
    elif kind == "weapon":
        # ROM olc_act.c:2306-2320
        wclass = _WEAPON_CLASS_NAMES.get(v[0], "exotic")
        out.append(f"[v0] Weapon class:   {wclass}")
        out.append(f"[v1] Number of dice: [{v[1]}]")
        out.append(f"[v2] Type of dice:   [{v[2]}]")
        attack_name = "none"
        if 0 <= v[3] < len(ATTACK_TABLE):
            entry = ATTACK_TABLE[v[3]]
            if entry.name is not None:
                attack_name = entry.name
        out.append(f"[v3] Type:           {attack_name}")
        out.append(f"[v4] Special type:   {_format_weapon_special(v[4])}")
    elif kind == "container":
        # ROM olc_act.c:2322-2335 — key-vnum->short_descr lookup omitted (display
        # only); ROM's "[v2] Key:     %s [%d]" simplified to show vnum only.
        out.append(f"[v0] Weight:     [{v[0]} kg]")
        out.append(f"[v1] Flags:      [{_format_container_flags(v[1])}]")
        out.append(f"[v2] Key:     [{v[2]}]")
        out.append(f"[v3] Capacity    [{v[3]}]")
        out.append(f"[v4] Weight Mult [{v[4]}]")
    elif kind in ("drink_con", "drinkcontainer"):
        # ROM olc_act.c:2337-2348
        liq_name = LIQUID_TABLE[v[2]].name if 0 <= v[2] < len(LIQUID_TABLE) else "unknown"
        out.append(f"[v0] Liquid Total: [{v[0]}]")
        out.append(f"[v1] Liquid Left:  [{v[1]}]")
        out.append(f"[v2] Liquid:       {liq_name}")
        out.append(f"[v3] Poisoned:     {'Yes' if v[3] != 0 else 'No'}")
    elif kind == "fountain":
        # ROM olc_act.c:2350-2358
        liq_name = LIQUID_TABLE[v[2]].name if 0 <= v[2] < len(LIQUID_TABLE) else "unknown"
        out.append(f"[v0] Liquid Total: [{v[0]}]")
        out.append(f"[v1] Liquid Left:  [{v[1]}]")
        out.append(f"[v2] Liquid:        {liq_name}")
    elif kind == "food":
        # ROM olc_act.c:2360-2368
        out.append(f"[v0] Food hours: [{v[0]}]")
        out.append(f"[v1] Full hours: [{v[1]}]")
        out.append(f"[v3] Poisoned:   {'Yes' if v[3] != 0 else 'No'}")
    elif kind == "money":
        # ROM olc_act.c:2370-2373
        out.append(f"[v0] Gold:   [{v[0]}]")
    # default: no values (matches ROM's `default: break;`)

    return out


def _oedit_show(obj_proto) -> str:
    """Mirroring ROM src/olc_act.c:2733-2812 oedit_show — emit object proto
    fields in ROM's exact line order/labels/column widths.
    """
    area = getattr(obj_proto, "area", None)
    area_vnum = -1 if area is None else int(getattr(area, "vnum", 0) or 0)
    area_name = "No Area" if area is None else (getattr(area, "name", None) or "No Area")
    name = obj_proto.name or ""
    item_type = obj_proto.item_type
    if isinstance(item_type, str):
        type_label = item_type.lower()
    else:
        type_label = str(item_type).lower()
    wear_flags = _coerce_int(getattr(obj_proto, "wear_flags", 0))
    extra_flags = _coerce_int(getattr(obj_proto, "extra_flags", 0))
    level = _coerce_int(getattr(obj_proto, "level", 0))
    weight = _coerce_int(getattr(obj_proto, "weight", 0))
    cost = _coerce_int(getattr(obj_proto, "cost", 0))
    condition = _coerce_int(getattr(obj_proto, "condition", 0))
    material = obj_proto.material or ""
    short_descr = obj_proto.short_descr or ""
    description = obj_proto.description or ""

    lines: list[str] = [
        f"Name:        [{name}]",
        f"Area:        [{area_vnum:5}] {area_name}",
        f"Vnum:        [{obj_proto.vnum:5}]",
        f"Type:        [{type_label}]",
        f"Level:       [{level:5}]",
        f"Wear flags:  [{_format_wear_flags(wear_flags)}]",
        f"Extra flags: [{_format_extra_flags(extra_flags)}]",
        f"Material:    [{material}]",
        f"Condition:   [{condition:5}]",
        f"Weight:      [{weight:5}]",
        f"Cost:        [{cost:5}]",
    ]

    # mirroring ROM olc_act.c:2776-2790 — Ex desc kwd row only when any present.
    extra_descrs = obj_proto.extra_descr or []
    if extra_descrs:
        keywords = "".join(
            f"[{(ed.get('keyword') if isinstance(ed, dict) else getattr(ed, 'keyword', '')) or ''}]"
            for ed in extra_descrs
        )
        lines.append(f"Ex desc kwd: {keywords}")

    # mirroring ROM olc_act.c:2792-2794 — Short desc + indented Long desc.
    lines.append(f"Short desc:  {short_descr}")
    lines.append(f"Long desc:\n     {description}")

    # mirroring ROM olc_act.c:2796-2807 — affects table only when any present.
    affects = getattr(obj_proto, "affected", None) or []
    for cnt, paf in enumerate(affects):
        if cnt == 0:
            lines.append("Number Modifier Affects")
            lines.append("------ -------- -------")
        location = _coerce_int(getattr(paf, "location", 0))
        modifier = _coerce_int(getattr(paf, "modifier", 0))
        loc_name = _APPLY_NAMES.get(location, "none")
        lines.append(f"[{cnt:4}] {modifier:<8} {loc_name}")

    # mirroring ROM olc_act.c:2809 — show_obj_values appended last.
    lines.extend(_show_obj_values(obj_proto))

    return "\n".join(lines)


def _handle_obj_extra_command(obj_proto, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: ed <add|desc|delete|list> ..."

    subcmd = args_parts[0].lower()
    rest = args_parts[1:]

    if subcmd == "list":
        if not obj_proto.extra_descr:
            return "No extra descriptions defined."
        lines = ["Extra descriptions:"]
        for extra in obj_proto.extra_descr:
            keyword = extra.get("keyword", "(none)")
            desc = extra.get("description", "(no description)")
            lines.append(f"- {keyword}: {desc}")
        return "\n".join(lines)

    if subcmd == "add":
        if not rest:
            return "Usage: ed add <keyword>"
        keyword = rest[0]
        if not isinstance(obj_proto.extra_descr, list):
            obj_proto.extra_descr = []
        for extra in obj_proto.extra_descr:
            if extra.get("keyword") == keyword:
                return f"Extra description '{keyword}' already exists. Use 'ed desc {keyword} <text>' to modify."
        obj_proto.extra_descr.append({"keyword": keyword, "description": ""})
        _mark_obj_changed(obj_proto)
        return f"Extra description '{keyword}' created. Use 'ed desc {keyword} <text>' to set the text."

    if subcmd in {"delete", "remove"}:
        if not rest:
            return "Usage: ed delete <keyword>"
        keyword = rest[0]
        if not isinstance(obj_proto.extra_descr, list):
            return f"No extra description named '{keyword}'."
        for i, extra in enumerate(obj_proto.extra_descr):
            if extra.get("keyword") == keyword:
                obj_proto.extra_descr.pop(i)
                _mark_obj_changed(obj_proto)
                return f"Extra description '{keyword}' removed."
        return f"No extra description named '{keyword}'."

    if subcmd in {"desc", "description"}:
        if len(rest) < 2:
            return "Usage: ed desc <keyword> <text>"
        keyword = rest[0]
        text = " ".join(rest[1:])
        if not isinstance(obj_proto.extra_descr, list):
            obj_proto.extra_descr = []
        for extra in obj_proto.extra_descr:
            if extra.get("keyword") == keyword:
                extra["description"] = text
                _mark_obj_changed(obj_proto)
                return f"Extra description '{keyword}' updated."
        obj_proto.extra_descr.append({"keyword": keyword, "description": text})
        _mark_obj_changed(obj_proto)
        return f"Extra description '{keyword}' created and set."

    return "Unknown extra description command."


def _mark_obj_changed(obj_proto) -> None:
    area = getattr(obj_proto, "area", None)
    if area:
        area.changed = True


def handle_oedit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_oedit(session, char, input_str)


def cmd_medit(char: Character, args: str) -> str:
    """Mobile editor - ROM src/olc.c:588-650."""
    session = _get_session(char)
    if session is None:
        return "You do not have an active connection."

    arg = args.strip()

    if session.editor == "medit":
        return _interpret_medit(session, char, arg)

    # mirrors ROM medit_table dispatch — explicit `create <vnum>` path.
    parts = arg.split(None, 1)
    if parts and parts[0].lower() == "create":
        rest = parts[1] if len(parts) > 1 else ""
        return _medit_create(session, char, rest)

    if not arg:
        return "Syntax: @medit <mobile vnum>"

    try:
        mob_vnum = int(arg)
    except ValueError:
        return "Mobile vnum must be a number."

    from mud.models.mob import mob_registry

    mob_proto = mob_registry.get(mob_vnum)
    if mob_proto is None:
        # mirrors ROM `do_medit` — without explicit `create`, unknown vnum is
        # an error, not auto-allocate.
        return "That mobile does not exist. Use 'medit create <vnum>' to create it."

    area = getattr(mob_proto, "area", None)
    if not _is_builder(char, area):
        return "Insufficient security to edit this mobile."

    _ensure_session_mob(session, mob_proto)
    return f"Now editing mobile {mob_proto.short_descr or '(unnamed)'} (vnum {mob_vnum}).\nType 'show' to display, 'done' to exit."


def _medit_create(session: Session, char: Character, argument: str) -> str:
    """Allocate a fresh mobile prototype.

    Mirrors ROM `medit_create` (`src/olc_act.c:3704-3753`). Defaults from
    `new_mob_index` (`src/mem.c:365-424`): player_name="no name",
    short_descr="(no short description)", long_descr="(no long description)\\n\\r",
    description="", level=0, sex=0 (NONE), size=SIZE_MEDIUM, start/default_pos=
    POS_STANDING, material="unknown", new_format=True. Critically, ROM sets
    `pMob->act = ACT_IS_NPC` (src/olc_act.c:3745) — without this, every NPC
    classification check downstream misclassifies the new mob as a player.
    """

    from mud.models.mob import MobIndex, mob_registry

    arg = argument.strip()
    try:
        vnum = int(arg) if arg else 0
    except ValueError:
        vnum = 0

    # mirrors ROM src/olc_act.c:3712-3716.
    if not arg or vnum == 0:
        return "Syntax:  medit create [vnum]\n\r"

    area = _get_area_for_vnum(vnum)
    # mirrors ROM src/olc_act.c:3718-3724.
    if area is None:
        return "MEdit:  That vnum is not assigned an area.\n\r"

    # mirrors ROM src/olc_act.c:3726-3730 — IS_BUILDER security gate.
    if not _is_builder(char, area):
        return "MEdit:  Vnum in an area you cannot build in.\n\r"

    # mirrors ROM src/olc_act.c:3732-3736.
    if vnum in mob_registry:
        return "MEdit:  Mobile vnum already exists.\n\r"

    proto = MobIndex(
        vnum=vnum,
        area=area,
        player_name="no name",
        short_descr="(no short description)",
        long_descr="(no long description)\n\r",
        description="",
        level=0,
        alignment=0,
        sex=Sex.NONE,
        size=Size.MEDIUM,
        start_pos="standing",
        default_pos="standing",
        material="unknown",
        wealth=0,
        new_format=True,
        # mirrors ROM src/olc_act.c:3745 — pMob->act = ACT_IS_NPC.
        act_flags=ActFlag.IS_NPC,
        act=int(ActFlag.IS_NPC),
    )
    mob_registry[vnum] = proto
    _ensure_session_mob(session, proto)
    return "Mobile Created.\n\r"


def _ensure_session_mob(session: Session, mob_proto) -> None:
    session.editor = "medit"
    session.editor_mode = EditorMode.MOBILE
    session.editor_state = {"mob_proto": mob_proto}


def _interpret_medit(session: Session, char: Character, raw_input: str) -> str:
    """Command interpreter for medit - ROM src/olc.c:medit_table."""
    from mud.models.mob import MobIndex

    mob_proto = session.editor_state.get("mob_proto") if session.editor_state else None
    if not isinstance(mob_proto, MobIndex):
        _clear_session(session)
        return "Mobile editor session lost. Type '@medit <vnum>' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: name <value> | short <value> | long <value> | level <num> | align <num> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid mobile editor syntax."

    if not parts:
        return "Syntax: name <value> | short <value> | long <value> | level <num> | align <num> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]

    if cmd == "@medit":
        if not args_parts:
            return "You are already editing this mobile."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd == "@asave":
        return cmd_asave(char, " ".join(parts[1:]) if len(parts) > 1 else "")

    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting mobile editor."

    if cmd == "create":
        # mirrors ROM medit_table dispatch — `create <vnum>` typed inside an
        # active medit session also allocates and switches the edit target.
        return _medit_create(session, char, " ".join(args_parts))

    if cmd == "commands":
        return _show_olc_cmds(_MEDIT_COMMANDS)

    if cmd == "show":
        return _medit_show(mob_proto)

    if cmd == "name":
        if not args_parts:
            return "Usage: name <player name>"
        new_name = " ".join(args_parts)
        mob_proto.player_name = new_name
        _mark_mob_changed(mob_proto)
        # mirroring ROM src/olc_act.c:3913-3931 medit_name — message verbatim.
        return "Name set."

    if cmd == "short":
        if not args_parts:
            return "Usage: short <short description>"
        new_short = " ".join(args_parts)
        mob_proto.short_descr = new_short
        _mark_mob_changed(mob_proto)
        return f"Short description set to: {new_short}"

    if cmd == "long":
        if not args_parts:
            return "Usage: long <long description>"
        new_long = " ".join(args_parts)
        mob_proto.long_descr = new_long
        _mark_mob_changed(mob_proto)
        return f"Long description set to: {new_long}"

    if cmd in {"desc", "description"}:
        if not args_parts:
            return "Usage: desc <description>"
        new_desc = " ".join(args_parts)
        mob_proto.description = new_desc
        _mark_mob_changed(mob_proto)
        return f"Description set to: {new_desc}"

    if cmd == "level":
        if not args_parts:
            return "Usage: level <number>"
        try:
            level = int(args_parts[0])
        except ValueError:
            return "Level must be a number."
        if level < 1:
            return "Level must be at least 1."
        mob_proto.level = level
        _mark_mob_changed(mob_proto)
        return f"Mobile level set to {level}."

    if cmd in {"align", "alignment"}:
        if not args_parts:
            return "Usage: align <number>"
        try:
            alignment = int(args_parts[0])
        except ValueError:
            return "Alignment must be a number."
        if alignment < -1000 or alignment > 1000:
            return "Alignment must be between -1000 and 1000."
        mob_proto.alignment = alignment
        _mark_mob_changed(mob_proto)
        return f"Alignment set to {alignment}."

    if cmd == "hitroll":
        if not args_parts:
            return "Usage: hitroll <number>"
        try:
            hitroll = int(args_parts[0])
        except ValueError:
            return "Hitroll must be a number."
        mob_proto.hitroll = hitroll
        _mark_mob_changed(mob_proto)
        return f"Hitroll set to {hitroll}."

    if cmd == "damroll":
        if not args_parts:
            return "Usage: damroll <number>"
        try:
            damroll = int(args_parts[0])
        except ValueError:
            return "Damroll must be a number."
        mob_proto.thac0 = damroll
        _mark_mob_changed(mob_proto)
        return f"Damroll set to {damroll}."

    if cmd == "race":
        if not args_parts:
            return "Usage: race <race name>"
        race = args_parts[0].lower()
        mob_proto.race = race
        _mark_mob_changed(mob_proto)
        return f"Race set to: {race}"

    if cmd == "sex":
        if not args_parts:
            return "Usage: sex <male|female|neutral|none>"
        sex_str = args_parts[0].lower()
        sex_map = {"male": 1, "female": 2, "neutral": 0, "none": 0}
        if sex_str not in sex_map:
            return "Sex must be male, female, neutral, or none."
        from mud.models.constants import Sex

        mob_proto.sex = Sex(sex_map[sex_str])
        _mark_mob_changed(mob_proto)
        return f"Sex set to: {sex_str}"

    if cmd == "wealth":
        if not args_parts:
            return "Usage: wealth <number>"
        try:
            wealth = int(args_parts[0])
        except ValueError:
            return "Wealth must be a number."
        if wealth < 0:
            return "Wealth must be non-negative."
        mob_proto.wealth = wealth
        _mark_mob_changed(mob_proto)
        return f"Wealth set to {wealth}."

    if cmd == "group":
        if not args_parts:
            return "Usage: group <number>"
        try:
            group = int(args_parts[0])
        except ValueError:
            return "Group must be a number."
        mob_proto.group = group
        _mark_mob_changed(mob_proto)
        return f"Group set to {group}."

    if cmd == "hit":
        if len(args_parts) < 1:
            return "Usage: hit <dice string> (e.g., 2d8+10)"
        hit_dice = args_parts[0]
        mob_proto.hit_dice = hit_dice
        _mark_mob_changed(mob_proto)
        return f"Hit dice set to: {hit_dice}"

    if cmd == "mana":
        if len(args_parts) < 1:
            return "Usage: mana <dice string> (e.g., 100d2+0)"
        mana_dice = args_parts[0]
        mob_proto.mana_dice = mana_dice
        _mark_mob_changed(mob_proto)
        return f"Mana dice set to: {mana_dice}"

    if cmd in {"dam", "damage"}:
        if len(args_parts) < 1:
            return "Usage: dam <dice string> (e.g., 1d6+2)"
        damage_dice = args_parts[0]
        mob_proto.damage_dice = damage_dice
        _mark_mob_changed(mob_proto)
        return f"Damage dice set to: {damage_dice}"

    if cmd == "damtype":
        if not args_parts:
            return "Usage: damtype <damage type>"
        damtype = " ".join(args_parts)
        mob_proto.damage_type = damtype
        _mark_mob_changed(mob_proto)
        return f"Damage type set to: {damtype}"

    if cmd == "ac":
        if len(args_parts) < 1:
            return "Usage: ac <dice string> (e.g., 6d1+0)"
        ac_dice = args_parts[0]
        mob_proto.ac = ac_dice
        _mark_mob_changed(mob_proto)
        return f"AC dice set to: {ac_dice}"

    if cmd == "material":
        if not args_parts:
            return "Usage: material <name>"
        material = " ".join(args_parts)
        mob_proto.material = material
        _mark_mob_changed(mob_proto)
        return f"Material set to: {material}"

    return f"Unknown mobile editor command: {cmd}"


def _format_intflag(enum_cls, bits: int) -> str:
    """Lowercase space-joined enum-name representation. Falls back to "none"
    when no bits are set. Note: ROM's display strings for these tables
    (act/affect/form/part/imm/res/vuln/off — `src/tables.c:82-690`) differ
    in some cases from Python enum-name lowercasing (e.g. ROM "stay_area"
    vs Python "STAY_AREA"). Tracked under OLC_ACT-010d.
    """
    bits = int(bits or 0)
    tokens = [m.name.lower() for m in enum_cls if int(m) and (bits & int(m)) == int(m)]
    return " ".join(tokens) if tokens else "none"


def _format_position(value) -> str:
    if isinstance(value, str):
        return value.lower() or "standing"
    try:
        return Position(int(value)).name.lower()
    except (TypeError, ValueError):
        return "standing"


def _format_size(value) -> str:
    if isinstance(value, Size):
        return value.name.lower()
    if isinstance(value, str):
        return value.lower() or "medium"
    try:
        return Size(int(value)).name.lower()
    except (TypeError, ValueError):
        return "medium"


def _format_race(value: object) -> str:
    if isinstance(value, str):
        return value
    try:
        race = get_race_by_index(int(value or 0))
    except (TypeError, ValueError):
        race = None
    return getattr(race, "name", None) or str(value)


def _format_sex(value) -> str:
    """Mirroring ROM olc_act.c:3537-3541 — pad male/female to 7 chars."""
    if hasattr(value, "name"):
        ival = int(value)
    elif isinstance(value, str):
        ival = {"male": 1, "female": 2, "either": 3, "random": 3}.get(value.lower(), 0)
    else:
        try:
            ival = int(value)
        except (TypeError, ValueError):
            ival = 0
    if ival == 1:
        return "male   "
    if ival == 2:
        return "female "
    if ival == 3:
        return "random "
    return "neutral"


def _medit_show(mob_proto) -> str:
    """Mirroring ROM src/olc_act.c:3519-3699 medit_show — emit mob proto
    fields in ROM's exact line order/labels.

    Sub-gaps documented but not closed in this commit:
    - OLC_ACT-010b: dice/AC stored as strings ("15d8+50") in Python; ROM
      stores 3 ints per dice. Emitted as-is in `[...]`.
    - OLC_ACT-010c: shop / mprogs / spec_fun rendering. ROM emits these
      conditionally; needs MobShop/MProg model alignment.
    - OLC_ACT-010d: ROM-faithful flag-table name strings (see
      `_format_intflag` docstring).
    """
    from mud.models.constants import (
        AffectFlag,
        FormFlag,
        ImmFlag,
        OffFlag,
        PartFlag,
        ResFlag,
        VulnFlag,
    )

    area = getattr(mob_proto, "area", None)
    area_vnum = -1 if area is None else int(getattr(area, "vnum", 0) or 0)
    area_name = "No Area" if area is None else (getattr(area, "name", None) or "No Area")
    name = mob_proto.player_name or ""
    act_bits = int(mob_proto.get_act_flags()) if hasattr(mob_proto, "get_act_flags") else _coerce_int(mob_proto.act_flags)
    sex = _format_sex(getattr(mob_proto, "sex", 0))
    race = _format_race(getattr(mob_proto, "race", ""))
    level = _coerce_int(getattr(mob_proto, "level", 0))
    align = _coerce_int(getattr(mob_proto, "alignment", 0))
    hitroll = _coerce_int(getattr(mob_proto, "hitroll", 0))
    dam_type_idx = _coerce_int(getattr(mob_proto, "dam_type", 0))
    if 0 <= dam_type_idx < len(ATTACK_TABLE) and ATTACK_TABLE[dam_type_idx].name:
        dam_type_name = ATTACK_TABLE[dam_type_idx].name
    else:
        dam_type_name = "none"
    affected_by = _coerce_int(getattr(mob_proto, "affected_by", 0))
    form = _coerce_int(getattr(mob_proto, "form", 0))
    parts = _coerce_int(getattr(mob_proto, "parts", 0))
    imm = _coerce_int(getattr(mob_proto, "imm_flags", 0))
    res = _coerce_int(getattr(mob_proto, "res_flags", 0))
    vuln = _coerce_int(getattr(mob_proto, "vuln_flags", 0))
    off = _coerce_int(getattr(mob_proto, "off_flags", 0))
    size = _format_size(getattr(mob_proto, "size", Size.MEDIUM))
    material = getattr(mob_proto, "material", "") or ""
    start_pos = _format_position(getattr(mob_proto, "start_pos", "standing"))
    default_pos = _format_position(getattr(mob_proto, "default_pos", "standing"))
    wealth = _coerce_int(getattr(mob_proto, "wealth", 0))
    group = _coerce_int(getattr(mob_proto, "group", 0))
    hit_dice = getattr(mob_proto, "hit_dice", "") or ""
    mana_dice = getattr(mob_proto, "mana_dice", "") or ""
    damage_dice = getattr(mob_proto, "damage_dice", "") or ""
    ac = getattr(mob_proto, "ac", "") or ""
    short_descr = (mob_proto.short_descr or "").rstrip("\n")
    long_descr = (mob_proto.long_descr or "").rstrip("\n")
    description = (mob_proto.description or "").rstrip("\n")

    lines: list[str] = [
        # mirroring ROM olc_act.c:3527-3535
        f"Name:        [{name}]",
        f"Area:        [{area_vnum:5}] {area_name}",
        f"Act:         [{_format_intflag(ActFlag, act_bits)}]",
        # mirroring ROM olc_act.c:3537-3548 — 3-up Vnum/Sex/Race; Level/Align/Hitroll/DamType.
        f"Vnum:        [{mob_proto.vnum:5}] Sex:   [{sex}]   Race: [{race}]",
        f"Level:       [{level:2}]    Align: [{align:4}]      Hitroll: [{hitroll:2}] Dam Type:    [{dam_type_name}]",
    ]
    if group:
        lines.append(f"Group:       [{group:5}]")
    # mirroring ROM olc_act.c:3557-3570 — dice rows (Python data model
    # uses string format; OLC_ACT-010b sub-gap).
    lines.append(f"Hit dice:    [{hit_dice}] Damage dice: [{damage_dice}] Mana dice:   [{mana_dice}]")
    # mirroring ROM olc_act.c:3574-3576
    lines.append(f"Affected by: [{_format_intflag(AffectFlag, affected_by)}]")
    # mirroring ROM olc_act.c:3580-3584 — armor display via raw AC string
    # (data-model divergence per OLC_ACT-010b).
    lines.append(f"Armor:       [pierce: {ac}  bash: {ac}  slash: {ac}  magic: {ac}]")
    # mirroring ROM olc_act.c:3586-3623
    lines.append(f"Form:        [{_format_intflag(FormFlag, form)}]")
    lines.append(f"Parts:       [{_format_intflag(PartFlag, parts)}]")
    lines.append(f"Imm:         [{_format_intflag(ImmFlag, imm)}]")
    lines.append(f"Res:         [{_format_intflag(ResFlag, res)}]")
    lines.append(f"Vuln:        [{_format_intflag(VulnFlag, vuln)}]")
    lines.append(f"Off:         [{_format_intflag(OffFlag, off)}]")
    lines.append(f"Size:        [{size}]")
    lines.append(f"Material:    [{material}]")
    lines.append(f"Start pos.   [{start_pos}]")
    lines.append(f"Default pos  [{default_pos}]")
    lines.append(f"Wealth:      [{wealth:5}]")
    # mirroring ROM olc_act.c:3636-3641
    lines.append(f"Short descr: {short_descr}")
    lines.append(f"Long descr:\n{long_descr}")
    lines.append(f"Description:\n{description}")

    # ROM olc_act.c:3643-3697 — shop / mprogs / spec_fun rendering deferred
    # to OLC_ACT-010c.

    return "\n".join(lines)


def _mark_mob_changed(mob_proto) -> None:
    area = getattr(mob_proto, "area", None)
    if area:
        area.changed = True


def handle_medit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_medit(session, char, input_str)


def cmd_rstat(char: Character, args: str) -> str:
    """Display detailed room statistics - ROM builder tool."""
    arg = args.strip()

    if not arg:
        room = getattr(char, "room", None)
        if room is None:
            return "You are not in a room."
    else:
        try:
            vnum = int(arg)
        except ValueError:
            return "Room vnum must be a number."
        room = room_registry.get(vnum)
        if room is None:
            return f"No room with vnum {vnum}."

    lines = []
    lines.append(f"Room: {room.name or '(unnamed)'}")
    lines.append(f"Vnum: {room.vnum}")
    lines.append(f"Description: {room.description or '(none)'}")

    area = getattr(room, "area", None)
    area_name = getattr(area, "name", "Unknown") if area else "None"
    lines.append(f"Area: {area_name}")

    sector_name = _SECTOR_NAMES.get(int(getattr(room, "sector_type", 0)), "unknown")
    lines.append(f"Sector: {sector_name}")

    room_flags = getattr(room, "room_flags", 0)
    flag_names = [name for bit, name in _ROOM_FLAG_DISPLAY if room_flags & bit]
    lines.append(f"Flags: {' '.join(flag_names) if flag_names else 'none'}")

    lines.append(f"Heal rate: {getattr(room, 'heal_rate', 100)}")
    lines.append(f"Mana rate: {getattr(room, 'mana_rate', 100)}")

    owner = getattr(room, "owner", "")
    lines.append(f"Owner: {owner if owner else 'none'}")

    clan_id = getattr(room, "clan", 0)
    if clan_id:
        clan = get_clan(clan_id)
        clan_name = getattr(clan, "name", f"clan{clan_id}") if clan else f"clan{clan_id}"
        lines.append(f"Clan: {clan_name}")

    exits = getattr(room, "exits", [])
    if any(exits):
        lines.append("\nExits:")
        for dir_val, exit_obj in enumerate(exits):
            if exit_obj is not None:
                dir_name = Direction(dir_val).name.lower()
                to_vnum = getattr(exit_obj, "vnum", 0)
                keyword = getattr(exit_obj, "keyword", None)
                exit_info = getattr(exit_obj, "exit_info", 0)
                flag_names = [name for bit, name in _EXIT_FLAG_DISPLAY if exit_info & bit]
                flags_str = f" [{' '.join(flag_names)}]" if flag_names else ""
                keyword_str = f" ({keyword})" if keyword else ""
                lines.append(f"  {dir_name}: {to_vnum}{keyword_str}{flags_str}")

    extra_descr = getattr(room, "extra_descr", [])
    if extra_descr:
        lines.append(f"\nExtra descriptions: {len(extra_descr)}")
        for extra in extra_descr[:5]:
            keyword = getattr(extra, "keyword", "(none)")
            lines.append(f"  - {keyword}")
        if len(extra_descr) > 5:
            lines.append(f"  ... and {len(extra_descr) - 5} more")

    return "\n".join(lines)


def cmd_ostat(char: Character, args: str) -> str:
    """Display detailed object statistics - ROM builder tool."""
    from mud.models.obj import obj_index_registry

    arg = args.strip()
    if not arg:
        return "Syntax: @ostat <vnum>"

    try:
        vnum = int(arg)
    except ValueError:
        return "Object vnum must be a number."

    obj_proto = obj_index_registry.get(vnum)
    if obj_proto is None:
        return f"No object prototype with vnum {vnum}."

    lines = []
    lines.append(f"Object: {obj_proto.short_descr or '(unnamed)'}")
    lines.append(f"Vnum: {vnum}")
    lines.append(f"Name: {obj_proto.name or '(none)'}")
    lines.append(f"Short: {obj_proto.short_descr or '(none)'}")
    lines.append(f"Long: {obj_proto.description or '(none)'}")
    lines.append(f"Type: {obj_proto.item_type}")
    lines.append(f"Level: {obj_proto.level}")
    lines.append(f"Weight: {obj_proto.weight}")
    lines.append(f"Cost: {obj_proto.cost}")
    lines.append(f"Material: {obj_proto.material or '(none)'}")
    lines.append(f"Condition: {obj_proto.condition}")

    value_list = obj_proto.value if isinstance(obj_proto.value, list) else [0, 0, 0, 0, 0]
    values_str = " ".join(str(v) for v in value_list[:5])
    lines.append(f"Values: {values_str}")

    area = getattr(obj_proto, "area", None)
    area_name = getattr(area, "name", "Unknown") if area else "None"
    lines.append(f"Area: {area_name}")

    extra_descr = getattr(obj_proto, "extra_descr", [])
    if extra_descr:
        lines.append(f"\nExtra descriptions: {len(extra_descr)}")
        for extra in extra_descr[:3]:
            keyword = extra.get("keyword", "(none)")
            lines.append(f"  - {keyword}")
        if len(extra_descr) > 3:
            lines.append(f"  ... and {len(extra_descr) - 3} more")

    affects = getattr(obj_proto, "affects", [])
    if affects:
        lines.append(f"\nAffects: {len(affects)}")
        for aff in affects[:5]:
            if isinstance(aff, dict):
                loc = aff.get("location", "unknown")
                mod = aff.get("modifier", 0)
                lines.append(f"  {loc}: {mod:+d}")
        if len(affects) > 5:
            lines.append(f"  ... and {len(affects) - 5} more")

    return "\n".join(lines)


def cmd_mstat(char: Character, args: str) -> str:
    """Display detailed mobile statistics - ROM builder tool."""
    from mud.models.mob import mob_registry

    arg = args.strip()
    if not arg:
        return "Syntax: @mstat <vnum>"

    try:
        vnum = int(arg)
    except ValueError:
        return "Mobile vnum must be a number."

    mob_proto = mob_registry.get(vnum)
    if mob_proto is None:
        return f"No mobile prototype with vnum {vnum}."

    lines = []
    lines.append(f"Mobile: {mob_proto.short_descr or '(unnamed)'}")
    lines.append(f"Vnum: {vnum}")
    lines.append(f"Name: {mob_proto.player_name or '(none)'}")
    lines.append(f"Short: {mob_proto.short_descr or '(none)'}")
    lines.append(f"Long: {mob_proto.long_descr or '(none)'}")
    lines.append(f"Description: {mob_proto.description or '(none)'}")
    lines.append(f"Level: {mob_proto.level}")
    lines.append(f"Alignment: {mob_proto.alignment}")
    lines.append(f"Hitroll: {mob_proto.hitroll}")
    lines.append(f"Race: {_format_race(getattr(mob_proto, 'race', ''))}")

    sex_val = mob_proto.sex
    if hasattr(sex_val, "name"):
        sex_str = sex_val.name.lower()
    elif sex_val == 1:
        sex_str = "male"
    elif sex_val == 2:
        sex_str = "female"
    else:
        sex_str = "none"
    lines.append(f"Sex: {sex_str}")

    lines.append(f"Wealth: {mob_proto.wealth}")
    lines.append(f"Group: {mob_proto.group}")
    lines.append(f"Hit dice: {mob_proto.hit_dice}")
    lines.append(f"Mana dice: {mob_proto.mana_dice}")
    lines.append(f"Damage dice: {mob_proto.damage_dice}")
    lines.append(f"Damage type: {mob_proto.damage_type}")
    lines.append(f"AC: {mob_proto.ac}")
    lines.append(f"Material: {mob_proto.material or '(none)'}")

    area = getattr(mob_proto, "area", None)
    area_name = getattr(area, "name", "Unknown") if area else "None"
    lines.append(f"Area: {area_name}")

    spec_fun = getattr(mob_proto, "spec_fun", None)
    if spec_fun:
        lines.append(f"Special function: {spec_fun}")

    shop = getattr(mob_proto, "pShop", None)
    if shop:
        lines.append("Has shop")

    return "\n".join(lines)


def cmd_goto(char: Character, args: str) -> str:
    """Teleport to a room vnum - ROM builder tool."""
    arg = args.strip()

    if not arg:
        return "Syntax: @goto <room vnum>"

    try:
        vnum = int(arg)
    except ValueError:
        return "Room vnum must be a number."

    target_room = room_registry.get(vnum)
    if target_room is None:
        return f"No room with vnum {vnum}."

    old_room = getattr(char, "room", None)
    char.room = target_room

    if old_room and old_room != target_room:
        return f"You teleport from {old_room.vnum} to {target_room.vnum}.\n{target_room.name}"
    else:
        return f"You arrive at {target_room.name} [{vnum}]."


def cmd_vlist(char: Character, args: str) -> str:
    """List all vnums in an area - ROM builder tool."""
    arg = args.strip()

    if not arg:
        current_room = getattr(char, "room", None)
        if current_room:
            area = getattr(current_room, "area", None)
        else:
            area = None
        if area is None:
            return "Syntax: @vlist <area vnum>"
    else:
        try:
            area_vnum = int(arg)
        except ValueError:
            return "Area vnum must be a number."
        area = area_registry.get(area_vnum)
        if area is None:
            return f"No area with vnum {area_vnum}."

    from mud.models.mob import mob_registry
    from mud.models.obj import obj_index_registry

    area_name = getattr(area, "name", "Unknown")
    min_vnum = getattr(area, "min_vnum", 0)
    max_vnum = getattr(area, "max_vnum", 0)

    lines = []
    lines.append(f"Area: {area_name} (vnums {min_vnum}-{max_vnum})")
    lines.append("")

    rooms = [vnum for vnum in room_registry.keys() if min_vnum <= vnum <= max_vnum]
    if rooms:
        rooms.sort()
        lines.append(f"Rooms ({len(rooms)}):")
        for vnum in rooms[:20]:
            room = room_registry[vnum]
            name = getattr(room, "name", "(unnamed)")
            lines.append(f"  [{vnum}] {name}")
        if len(rooms) > 20:
            lines.append(f"  ... and {len(rooms) - 20} more")
        lines.append("")

    mobs = [vnum for vnum in mob_registry.keys() if min_vnum <= vnum <= max_vnum]
    if mobs:
        mobs.sort()
        lines.append(f"Mobiles ({len(mobs)}):")
        for vnum in mobs[:20]:
            mob = mob_registry[vnum]
            name = getattr(mob, "short_descr", "(unnamed)")
            lines.append(f"  [{vnum}] {name}")
        if len(mobs) > 20:
            lines.append(f"  ... and {len(mobs) - 20} more")
        lines.append("")

    objs = [vnum for vnum in obj_index_registry.keys() if min_vnum <= vnum <= max_vnum]
    if objs:
        objs.sort()
        lines.append(f"Objects ({len(objs)}):")
        for vnum in objs[:20]:
            obj = obj_index_registry[vnum]
            name = getattr(obj, "short_descr", "(unnamed)")
            lines.append(f"  [{vnum}] {name}")
        if len(objs) > 20:
            lines.append(f"  ... and {len(objs) - 20} more")

    return "\n".join(lines)


def cmd_hedit(char: Character, args: str) -> str:
    """Help file editor - ROM builder tool."""
    from mud.models.help import HelpEntry, help_registry

    session = _get_session(char)
    if session is None:
        return "You do not have an active connection."

    arg = args.strip()

    if session.editor != "hedit" and not _has_help_security(char):
        return "HEdit: Insufficient security to edit helps."

    if session.editor == "hedit":
        return _interpret_hedit(session, char, arg)

    if not arg:
        return "Syntax: @hedit <keyword> or @hedit new"

    if arg.lower() == "new":
        new_help = HelpEntry(keywords=["new"], text="", level=0)
        _ensure_session_help(session, new_help, is_new=True)
        return "Creating new help entry.\nType 'keywords <word word>' to set keywords, 'text <content>' for text, 'done' to save."

    keyword = arg.lower()
    entries = help_registry.get(keyword, [])

    if not entries:
        new_help = HelpEntry(keywords=[keyword], text="", level=0)
        _ensure_session_help(session, new_help, is_new=True)
        return f"Creating new help entry for '{keyword}'.\nType 'text <content>' to set text, 'level <num>' for level, 'done' to save."

    help_entry = entries[0]
    _ensure_session_help(session, help_entry, is_new=False)
    return f"Editing help entry: {' '.join(help_entry.keywords)}\nType 'show' to display, 'done' to save."


def _ensure_session_help(session: Session, help_entry, is_new: bool = False) -> None:
    session.editor = "hedit"
    session.editor_mode = EditorMode.HELP
    session.editor_state = {
        "help": help_entry,
        "is_new": is_new,
        "original_keywords": list(getattr(help_entry, "keywords", []) or []),
    }


def _reindex_help_entry(help_entry, original_keywords: list[str]) -> None:
    from mud.models.help import help_registry, register_help

    for keyword in original_keywords:
        key = keyword.lower()
        bucket = help_registry.get(key)
        if not bucket:
            continue
        if help_entry in bucket:
            bucket.remove(help_entry)
        if not bucket:
            help_registry.pop(key, None)
    register_help(help_entry)


def _interpret_hedit(session: Session, char: Character, raw_input: str) -> str:
    """Command interpreter for hedit."""
    from mud.models.help import HelpEntry, register_help

    help_entry = session.editor_state.get("help") if session.editor_state else None
    if not isinstance(help_entry, HelpEntry):
        _clear_session(session)
        return "Help editor session lost. Type '@hedit <keyword>' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: keywords <words> | text <content> | level <num> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid help editor syntax."

    if not parts:
        return "Syntax: keywords <words> | text <content> | level <num> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]

    if cmd == "@hedit":
        if not args_parts:
            return "You are already editing this help entry."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd in {"done", "exit"}:
        is_new = session.editor_state.get("is_new", False)
        original_keywords = session.editor_state.get("original_keywords", list(help_entry.keywords))
        if is_new:
            register_help(help_entry)
        else:
            previous = [keyword.lower() for keyword in original_keywords if keyword]
            current = [keyword.lower() for keyword in help_entry.keywords if keyword]
            if previous != current:
                _reindex_help_entry(help_entry, original_keywords)
        _clear_session(session)
        return "Help entry saved. Use '@hesave' to write to disk."

    if cmd == "commands":
        return _show_olc_cmds(_HEDIT_COMMANDS)

    if cmd == "show":
        return _hedit_show(help_entry)

    if cmd in {"keywords", "keyword"}:
        if not args_parts:
            return "Usage: keywords <word word word>"
        new_keywords = [w.lower() for w in args_parts]
        help_entry.keywords = new_keywords
        return f"Keywords set to: {' '.join(new_keywords)}"

    if cmd == "text":
        if not args_parts:
            return "Usage: text <help text content>"
        new_text = " ".join(args_parts)
        help_entry.text = new_text
        return "Help text updated."

    if cmd == "level":
        if not args_parts:
            return "Usage: level <number>"
        try:
            level = int(args_parts[0])
        except ValueError:
            return "Level must be a number."
        if level < 0:
            return "Level must be non-negative."
        help_entry.level = level
        return f"Level set to {level}."

    return f"Unknown help editor command: {cmd}"


def _hedit_show(help_entry) -> str:
    lines = []
    lines.append(f"Keywords: {' '.join(help_entry.keywords)}")
    lines.append(f"Level:    {help_entry.level}")
    lines.append(f"Text:     {help_entry.text[:100]}{'...' if len(help_entry.text) > 100 else ''}")
    return "\n".join(lines)


def cmd_hesave(char: Character, args: str, help_file: Path | None = None) -> str:
    """Save help files to disk - ROM builder tool.

    Args:
        char: Character executing the command
        args: Command arguments (unused)
        help_file: Optional path for testing; defaults to data/help.json
    """
    from mud.models.help import help_entries

    if not _has_help_security(char):
        return "HEdit: Insufficient security to edit helps."

    if help_file is None:
        help_file = Path("data/help.json")

    help_data = []
    for entry in help_entries:
        help_data.append({"keywords": entry.keywords, "level": entry.level, "text": entry.text})

    try:
        with open(help_file, "w") as f:
            json.dump(help_data, f, indent=2)
        return f"Saved {len(help_data)} help entries to {help_file}"
    except Exception as e:
        return f"Error saving help file: {e}"


def handle_hedit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_hedit(session, char, input_str)
