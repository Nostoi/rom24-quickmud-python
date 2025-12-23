from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntFlag
from typing import TYPE_CHECKING

from mud.models.constants import ActFlag, AffectFlag, Direction, ImmFlag, ItemType, OffFlag, Position
from mud.models.mob import MobProgram
from mud.utils import rng_mm

if TYPE_CHECKING:
    from mud.models.character import Character


class Trigger(IntFlag):
    """Bit flags describing mob program trigger types."""

    ACT = 1 << 0
    BRIBE = 1 << 1
    DEATH = 1 << 2
    ENTRY = 1 << 3
    FIGHT = 1 << 4
    GIVE = 1 << 5
    GREET = 1 << 6
    GRALL = 1 << 7
    KILL = 1 << 8
    HPCNT = 1 << 9
    RANDOM = 1 << 10
    SPEECH = 1 << 11
    EXIT = 1 << 12
    EXALL = 1 << 13
    DELAY = 1 << 14
    SURR = 1 << 15


@dataclass
class ExecutionResult:
    """Represents a single action performed by the interpreter."""

    command: str
    argument: str
    mob_command: bool = False


@dataclass
class ProgramContext:
    """Execution context shared across nested ``mpcall`` invocations."""

    mob: object
    results: list[ExecutionResult] = field(default_factory=list)
    call_level: int = 0

    def push(self) -> bool:
        self.call_level += 1
        if self.call_level > MAX_CALL_LEVEL:
            self.call_level -= 1
            return False
        return True

    def pop(self) -> None:
        if self.call_level > 0:
            self.call_level -= 1

    def record(self, command: str, argument: str, *, mob_command: bool = False) -> None:
        self.results.append(ExecutionResult(command=command, argument=argument, mob_command=mob_command))


MAX_NESTED_LEVEL = 12
BEGIN_BLOCK = 0
IN_BLOCK = -1
END_BLOCK = -2
MAX_CALL_LEVEL = 5

_PROGRAM_REGISTRY: dict[int, MobProgram] = {}

_TRIGGER_NAME_MAP: dict[str, Trigger] = {
    "act": Trigger.ACT,
    "bribe": Trigger.BRIBE,
    "death": Trigger.DEATH,
    "entry": Trigger.ENTRY,
    "fight": Trigger.FIGHT,
    "give": Trigger.GIVE,
    "greet": Trigger.GREET,
    "grall": Trigger.GRALL,
    "kill": Trigger.KILL,
    "hpcnt": Trigger.HPCNT,
    "random": Trigger.RANDOM,
    "speech": Trigger.SPEECH,
    "exit": Trigger.EXIT,
    "exall": Trigger.EXALL,
    "delay": Trigger.DELAY,
    "surr": Trigger.SURR,
    "surrender": Trigger.SURR,
}

_CANONICAL_TRIGGER_NAMES: dict[Trigger, str] = {
    Trigger.ACT: "ACT",
    Trigger.BRIBE: "BRIBE",
    Trigger.DEATH: "DEATH",
    Trigger.ENTRY: "ENTRY",
    Trigger.FIGHT: "FIGHT",
    Trigger.GIVE: "GIVE",
    Trigger.GREET: "GREET",
    Trigger.GRALL: "GRALL",
    Trigger.KILL: "KILL",
    Trigger.HPCNT: "HPCNT",
    Trigger.RANDOM: "RANDOM",
    Trigger.SPEECH: "SPEECH",
    Trigger.EXIT: "EXIT",
    Trigger.EXALL: "EXALL",
    Trigger.DELAY: "DELAY",
    Trigger.SURR: "SURRENDER",
}


def _register_program(prog: MobProgram) -> None:
    vnum = int(getattr(prog, "vnum", 0) or 0)
    code = getattr(prog, "code", None)
    if vnum > 0 and code:
        _PROGRAM_REGISTRY[vnum] = prog


def clear_registered_programs() -> None:
    """Reset the cached mob program registry (primarily for tests)."""

    _PROGRAM_REGISTRY.clear()


def get_registered_program(vnum: int) -> MobProgram | None:
    """Return the cached program for ``vnum`` if one is registered."""

    return _PROGRAM_REGISTRY.get(int(vnum))


def resolve_trigger_flag(name: str) -> Trigger | None:
    """Translate an ``M`` line trigger keyword into a :class:`Trigger`."""

    if not name:
        return None
    return _TRIGGER_NAME_MAP.get(name.lower())


def format_trigger_flag(value: int | Trigger) -> str:
    """Return the ROM keyword for the provided trigger flag."""

    try:
        trigger = Trigger(int(value))
    except (ValueError, TypeError):
        return ""
    return _CANONICAL_TRIGGER_NAMES.get(trigger, "")


def register_program_code(vnum: int, code: str) -> None:
    """Record program ``code`` and link it to any existing trigger entries."""

    if int(vnum) <= 0:
        return
    attached = _attach_code_to_existing_programs(vnum, code)
    if not attached:
        _register_program(MobProgram(trig_type=0, vnum=vnum, code=code))


def _attach_code_to_existing_programs(vnum: int, code: str) -> bool:
    from mud.registry import mob_registry

    attached = False
    for mob in mob_registry.values():
        for entry in getattr(mob, "mprogs", []) or []:
            if int(getattr(entry, "vnum", 0) or 0) != int(vnum):
                continue
            entry.code = code
            _register_program(entry)
            attached = True
    return attached


def _get_registered_program(vnum: int) -> MobProgram | None:
    return _PROGRAM_REGISTRY.get(int(vnum))


def _get_programs(mob: object) -> list[MobProgram]:
    programs: list[MobProgram] = []
    direct = getattr(mob, "mob_programs", None)
    if direct:
        programs.extend(direct)
    proto = getattr(mob, "prototype", None) or getattr(mob, "mob_index", None)
    if proto:
        programs.extend(getattr(proto, "mprogs", []) or [])
    seen: set[int] = set()
    unique: list[MobProgram] = []
    for prog in programs:
        if prog is None or getattr(prog, "code", None) is None:
            continue
        ident = id(prog)
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(prog)
    return unique


def _can_see(mob: object, target: object | None) -> bool:
    from mud.world.vision import can_see_character

    if mob is None or target is None:
        return False
    try:
        return bool(can_see_character(mob, target))
    except Exception:
        room = getattr(mob, "room", None)
        if room is None:
            return False
        return target in getattr(room, "people", [])


def _get_random_char(mob: object) -> object | None:
    room = getattr(mob, "room", None)
    if room is None:
        return None
    winner = None
    highest = -1
    for occupant in getattr(room, "people", []) or []:
        if occupant is mob:
            continue
        if getattr(occupant, "is_npc", False):
            continue
        if not _can_see(mob, occupant):
            continue
        roll = rng_mm.number_percent()
        if roll > highest:
            highest = roll
            winner = occupant
    return winner


def _match_name(name: object, token: str) -> bool:
    if not token:
        return False
    if not name:
        return False
    lowered = token.lower()
    for part in str(name).split():
        if lowered == part.lower():
            return True
    return False


def _iter_carried_objects(char: object) -> list[object]:
    carried: list[object] = []
    for obj in getattr(char, "inventory", []) or []:
        carried.append(obj)
    equipment = getattr(char, "equipment", {}) or {}
    for obj in equipment.values():
        if obj is not None:
            carried.append(obj)
    return carried


def _iter_worn_objects(char: object) -> list[object]:
    equipment = getattr(char, "equipment", {}) or {}
    return [obj for obj in equipment.values() if obj is not None]


def _object_vnum(obj: object) -> int | None:
    proto = getattr(obj, "prototype", None)
    if proto is None:
        return None
    return getattr(proto, "vnum", None)


def _object_item_type(obj: object) -> int | None:
    proto = getattr(obj, "prototype", None)
    if proto is None:
        return None
    raw_type = getattr(proto, "item_type", None)
    if raw_type is None:
        return None
    if isinstance(raw_type, int):
        return raw_type
    if isinstance(raw_type, ItemType):
        return int(raw_type)
    try:
        return int(raw_type)
    except (TypeError, ValueError):
        pass
    try:
        return ItemType[str(raw_type).upper()].value
    except (AttributeError, KeyError, ValueError):
        return None


def _character_has_item(
    char: object,
    *,
    vnum: int | None = None,
    item_type: int | None = None,
    require_worn: bool = False,
    name: str | None = None,
) -> bool:
    if char is None:
        return False
    objects = _iter_worn_objects(char) if require_worn else _iter_carried_objects(char)
    for obj in objects:
        proto = getattr(obj, "prototype", None)
        if proto is None:
            continue
        if vnum is not None:
            obj_vnum = _object_vnum(obj)
            if obj_vnum is None or int(obj_vnum) != vnum:
                continue
        if item_type is not None:
            obj_type = _object_item_type(obj)
            if obj_type is None or int(obj_type) != item_type:
                continue
        if name is not None:
            obj_name = getattr(proto, "name", None) or getattr(obj, "name", None)
            obj_short = getattr(proto, "short_descr", None)
            if not (_match_name(obj_name, name) or _match_name(obj_short, name)):
                continue
        return True
    return False


def _lookup_item_type(token: str) -> int | None:
    if not token:
        return None
    try:
        return ItemType[token.upper()].value
    except KeyError:
        return None


def _character_proto_vnum(char: object) -> int | None:
    for attr in ("prototype", "mob_index"):
        proto = getattr(char, attr, None)
        if proto is not None:
            vnum = getattr(proto, "vnum", None)
            if vnum is not None:
                try:
                    return int(vnum)
                except (TypeError, ValueError):
                    continue
    return None


def _count_people_room(mob: object, flag: int) -> int:
    room = getattr(mob, "room", None)
    if room is None:
        return 0
    count = 0
    mob_vnum = _character_proto_vnum(mob)
    for occupant in getattr(room, "people", []) or []:
        if occupant is mob:
            continue
        is_npc = bool(getattr(occupant, "is_npc", False))
        if flag == 1 and is_npc:
            continue
        if flag == 2 and not is_npc:
            continue
        if flag == 3:
            if not (is_npc and bool(getattr(mob, "is_npc", False))):
                continue
            if mob_vnum is None or _character_proto_vnum(occupant) != mob_vnum:
                continue
        if flag == 4:
            mob_leader = getattr(mob, "leader", None) or mob
            occupant_leader = getattr(occupant, "leader", None) or occupant
            if not (
                occupant is getattr(mob, "master", None)
                or mob is getattr(occupant, "master", None)
                or occupant_leader is mob_leader
            ):
                continue
        if not _can_see(mob, occupant):
            continue
        count += 1
    return count


def _get_order(mob: object) -> int:
    if not getattr(mob, "is_npc", False):
        return 0
    room = getattr(mob, "room", None)
    if room is None:
        return 0
    mob_vnum = _character_proto_vnum(mob)
    if mob_vnum is None:
        return 0
    order = 0
    for occupant in getattr(room, "people", []) or []:
        if occupant is mob:
            return order
        if getattr(occupant, "is_npc", False) and _character_proto_vnum(occupant) == mob_vnum:
            order += 1
    return 0


def _mob_here(mob: object, identifier: str) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not identifier:
        return False
    people = getattr(room, "people", []) or []
    if identifier.isdigit():
        target_vnum = int(identifier)
        for occupant in people:
            if occupant is mob:
                continue
            if _character_proto_vnum(occupant) == target_vnum:
                return True
        return False
    for occupant in people:
        if occupant is mob:
            continue
        if _match_name(getattr(occupant, "name", None), identifier) or _match_name(
            getattr(occupant, "short_descr", None), identifier
        ):
            return True
    return False


def _obj_here(mob: object, identifier: str) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not identifier:
        return False
    contents = getattr(room, "contents", []) or []
    if identifier.isdigit():
        target_vnum = int(identifier)
        for obj in contents:
            if _object_vnum(obj) == target_vnum:
                return True
        return False
    for obj in contents:
        proto = getattr(obj, "prototype", None)
        if proto is None:
            continue
        if _match_name(getattr(proto, "name", None), identifier) or _match_name(
            getattr(proto, "short_descr", None), identifier
        ):
            return True
    return False


def _current_hour() -> int:
    try:
        from mud.time import time_info
    except ImportError:
        return 0
    return int(getattr(time_info, "hour", 0))


def _resolve_character_token(
    token: str,
    mob: object,
    ch: object | None,
    arg1: object | None,
    arg2: object | None,
    rch: object | None,
) -> object | None:
    if not token:
        return None
    code = token[1] if token.startswith("$") and len(token) > 1 else token[0]
    if code == "i":
        return mob
    if code == "n":
        return ch if hasattr(ch, "is_npc") else None
    if code == "t":
        return arg2 if hasattr(arg2, "is_npc") else None
    if code == "r":
        return rch if rch else _get_random_char(mob)
    if code == "q":
        target = getattr(mob, "mprog_target", None)
        return target if hasattr(target, "is_npc") else None
    return None


def _resolve_object_token(token: str, arg1: object | None, arg2: object | None) -> object | None:
    if not token:
        return None
    code = token[1] if token.startswith("$") and len(token) > 1 else token[0]
    if code in {"o", "O"}:
        return arg1 if hasattr(arg1, "prototype") else None
    if code in {"p", "P"}:
        return arg2 if hasattr(arg2, "prototype") else None
    return None


def _expand_arg(
    format_str: str,
    mob: object,
    ch: object | None,
    arg1: object | None,
    arg2: object | None,
    rch: object | None,
) -> str:
    if not format_str:
        return ""
    he_she = ["it", "he", "she"]
    him_her = ["it", "him", "her"]
    his_her = ["its", "his", "her"]
    someone = "someone"
    someones = "someone's"
    something = "something"
    result: list[str] = []
    idx = 0
    while idx < len(format_str):
        if format_str[idx] != "$":
            result.append(format_str[idx])
            idx += 1
            continue
        idx += 1
        if idx >= len(format_str):
            break
        code = format_str[idx]
        idx += 1
        substitution = ""
        if code == "i":
            name = getattr(mob, "name", None) or getattr(mob, "short_descr", None) or "someone"
            substitution = str(name).split()[0]
        elif code == "I":
            substitution = getattr(mob, "short_descr", None) or getattr(mob, "name", None) or "someone"
        elif code == "n":
            target = ch if hasattr(ch, "is_npc") else None
            if target and _can_see(mob, target):
                substitution = (getattr(target, "name", None) or someone).split()[0].capitalize()
            else:
                substitution = someone
        elif code == "N":
            target = ch if hasattr(ch, "is_npc") else None
            if target and _can_see(mob, target):
                substitution = getattr(target, "short_descr", None) or getattr(target, "name", None) or someone
            else:
                substitution = someone
        elif code == "r":
            pick = rch if rch else _get_random_char(mob)
            if pick and _can_see(mob, pick):
                substitution = (getattr(pick, "name", None) or someone).split()[0].capitalize()
            else:
                substitution = someone
        elif code == "R":
            pick = rch if rch else _get_random_char(mob)
            if pick and _can_see(mob, pick):
                substitution = getattr(pick, "short_descr", None) or getattr(pick, "name", None) or someone
            else:
                substitution = someone
        elif code == "q":
            target = getattr(mob, "mprog_target", None)
            if target and _can_see(mob, target):
                substitution = (getattr(target, "name", None) or someone).split()[0].capitalize()
            else:
                substitution = someone
        elif code == "Q":
            target = getattr(mob, "mprog_target", None)
            if target and _can_see(mob, target):
                substitution = getattr(target, "short_descr", None) or getattr(target, "name", None) or someone
            else:
                substitution = someone
        elif code == "j":
            sex = int(getattr(mob, "sex", 0) or 0)
            substitution = he_she[max(0, min(sex, 2))]
        elif code == "t":
            target = arg2 if hasattr(arg2, "is_npc") else None
            if target and _can_see(mob, target):
                substitution = (getattr(target, "name", None) or someone).split()[0].capitalize()
            else:
                substitution = someone
        elif code == "T":
            target = arg2 if hasattr(arg2, "is_npc") else None
            if target and _can_see(mob, target):
                substitution = getattr(target, "short_descr", None) or getattr(target, "name", None) or someone
            else:
                substitution = someone
        elif code == "e":
            target = ch if hasattr(ch, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = he_she[max(0, min(sex, 2))] if target else someone
        elif code == "E":
            target = arg2 if hasattr(arg2, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = he_she[max(0, min(sex, 2))] if target else someone
        elif code == "J":
            pick = rch if rch else _get_random_char(mob)
            if pick and _can_see(mob, pick):
                sex = int(getattr(pick, "sex", 0) or 0)
                substitution = he_she[max(0, min(sex, 2))]
            else:
                substitution = someone
        elif code == "X":
            target = getattr(mob, "mprog_target", None)
            if target and _can_see(mob, target):
                sex = int(getattr(target, "sex", 0) or 0)
                substitution = he_she[max(0, min(sex, 2))]
            else:
                substitution = someone
        elif code == "m":
            target = ch if hasattr(ch, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = him_her[max(0, min(sex, 2))] if target else someone
        elif code == "M":
            target = arg2 if hasattr(arg2, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = him_her[max(0, min(sex, 2))] if target else someone
        elif code == "k":
            sex = int(getattr(mob, "sex", 0) or 0)
            substitution = him_her[max(0, min(sex, 2))]
        elif code == "K":
            pick = rch if rch else _get_random_char(mob)
            if pick and _can_see(mob, pick):
                sex = int(getattr(pick, "sex", 0) or 0)
                substitution = him_her[max(0, min(sex, 2))]
            else:
                substitution = someone
        elif code == "Y":
            target = getattr(mob, "mprog_target", None)
            if target and _can_see(mob, target):
                sex = int(getattr(target, "sex", 0) or 0)
                substitution = him_her[max(0, min(sex, 2))]
            else:
                substitution = someone
        elif code == "s":
            target = ch if hasattr(ch, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = his_her[max(0, min(sex, 2))] if target else someones
        elif code == "S":
            target = arg2 if hasattr(arg2, "sex") else None
            sex = int(getattr(target, "sex", 0)) if target else 0
            substitution = his_her[max(0, min(sex, 2))] if target else someones
        elif code == "l":
            sex = int(getattr(mob, "sex", 0) or 0)
            substitution = his_her[max(0, min(sex, 2))]
        elif code == "L":
            pick = rch if rch else _get_random_char(mob)
            if pick and _can_see(mob, pick):
                sex = int(getattr(pick, "sex", 0) or 0)
                substitution = his_her[max(0, min(sex, 2))]
            else:
                substitution = someones
        elif code == "Z":
            target = getattr(mob, "mprog_target", None)
            if target and _can_see(mob, target):
                sex = int(getattr(target, "sex", 0) or 0)
                substitution = his_her[max(0, min(sex, 2))]
            else:
                substitution = someones
        elif code in ("o", "O"):
            obj = arg1 if hasattr(arg1, "name") else None
            if code == "o":
                substitution = (getattr(obj, "name", None) or something).split()[0]
            else:
                substitution = getattr(obj, "short_descr", None) or getattr(obj, "name", None) or something
        elif code in ("p", "P"):
            obj = arg2 if hasattr(arg2, "name") else None
            if code == "p":
                substitution = (getattr(obj, "name", None) or something).split()[0]
            else:
                substitution = getattr(obj, "short_descr", None) or getattr(obj, "name", None) or something
        else:
            substitution = "$" + code
        result.append(substitution)
    return "".join(result)


def _compare_numbers(lval: int, oper: str, rval: int) -> bool:
    if oper == "==":
        return lval == rval
    if oper == ">=":
        return lval >= rval
    if oper == "<=":
        return lval <= rval
    if oper == ">":
        return lval > rval
    if oper == "<":
        return lval < rval
    if oper == "!=":
        return lval != rval
    return False


def _cmd_eval(
    check: str,
    arguments: str,
    mob: object,
    ch: object | None,
    arg1: object | None,
    arg2: object | None,
    rch: object | None,
) -> bool:
    tokens = arguments.split()
    check = check.lower()

    if getattr(mob, "mprog_target", None) is None and ch is not None:
        try:
            setattr(mob, "mprog_target", ch)
        except Exception:
            pass

    if check == "rand":
        if not tokens:
            return False
        try:
            limit = int(tokens[0])
        except ValueError:
            return False
        return rng_mm.number_percent() < limit

    if check == "mobhere":
        return _mob_here(mob, tokens[0] if tokens else "")
    if check == "objhere":
        return _obj_here(mob, tokens[0] if tokens else "")
    if check == "mobexists":
        if not tokens:
            return False
        identifier = tokens[0]
        try:
            from mud.models.character import character_registry
        except ImportError:
            character_registry = []
        if identifier.isdigit():
            target_vnum = int(identifier)
            return any(_character_proto_vnum(char) == target_vnum for char in character_registry)
        lowered = identifier.lower()
        return any(
            _match_name(getattr(char, "name", None), lowered)
            or _match_name(getattr(char, "short_descr", None), lowered)
            for char in character_registry
        )
    if check == "objexists":
        if not tokens:
            return False
        identifier = tokens[0]
        room = getattr(mob, "room", None)
        if room and _obj_here(mob, identifier):
            return True
        people = getattr(room, "people", []) if room else []
        for char in people or []:
            if identifier.isdigit():
                if _character_has_item(char, vnum=int(identifier)):
                    return True
            else:
                if _character_has_item(char, name=identifier):
                    return True
        for candidate in (arg1, arg2):
            if not hasattr(candidate, "prototype"):
                continue
            if identifier.isdigit():
                if _object_vnum(candidate) == int(identifier):
                    return True
            else:
                proto = getattr(candidate, "prototype", None)
                if proto and (
                    _match_name(getattr(proto, "name", None), identifier)
                    or _match_name(getattr(proto, "short_descr", None), identifier)
                ):
                    return True
        return False

    numeric_checks: dict[str, Callable[[], int]] = {
        "people": lambda: _count_people_room(mob, 0),
        "players": lambda: _count_people_room(mob, 1),
        "mobs": lambda: _count_people_room(mob, 2),
        "clones": lambda: _count_people_room(mob, 3),
        "order": lambda: _get_order(mob),
        "hour": _current_hour,
    }
    if check in numeric_checks:
        if len(tokens) < 2:
            return False
        oper = tokens[0]
        try:
            rval = int(tokens[1])
        except ValueError:
            return False
        try:
            lval = numeric_checks[check]()
        except Exception:
            return False
        return _compare_numbers(int(lval), oper, rval)

    if not tokens:
        return False

    token = tokens[0]
    code = token[1] if token.startswith("$") and len(token) > 1 else token[:1]
    target_char = _resolve_character_token(token, mob, ch, arg1, arg2, rch)
    target_obj = _resolve_object_token(token, arg1, arg2)
    has_target = target_char is not None or target_obj is not None

    if check == "exists":
        return has_target

    if not has_target:
        return False

    # Case 3: boolean checks on actors/objects
    if check == "ispc":
        return bool(target_char and not getattr(target_char, "is_npc", True))
    if check == "isnpc":
        return bool(target_char and getattr(target_char, "is_npc", False))
    if check == "isgood":
        return bool(target_char and int(getattr(target_char, "alignment", 0)) >= 350)
    if check == "isevil":
        return bool(target_char and int(getattr(target_char, "alignment", 0)) <= -350)
    if check == "isneutral":
        if target_char is None:
            return False
        align = int(getattr(target_char, "alignment", 0))
        return not (align >= 350 or align <= -350)
    if check == "isimmort":
        return bool(target_char and getattr(target_char, "is_immortal", lambda: False)())
    if check == "ischarm":
        return bool(target_char and hasattr(target_char, "has_affect") and target_char.has_affect(AffectFlag.CHARM))
    if check == "isfollow":
        if target_char is None:
            return False
        master = getattr(target_char, "master", None)
        return bool(master and getattr(master, "room", None) is getattr(target_char, "room", None))
    if check == "isactive":
        return bool(target_char and int(getattr(target_char, "position", Position.STANDING)) > int(Position.SLEEPING))
    if check == "isdelay":
        return bool(target_char and int(getattr(target_char, "mprog_delay", 0) or 0) > 0)
    if check == "isvisible":
        if code.lower() in {"o", "p"}:
            if target_obj is None:
                return False
            room = getattr(mob, "room", None)
            if room is None:
                return False
            if target_obj in getattr(room, "contents", []):
                return True
            return getattr(target_obj, "location", None) is room
        return bool(target_char and _can_see(mob, target_char))
    if check == "hastarget":
        if target_char is None:
            return False
        target = getattr(target_char, "mprog_target", None)
        return bool(target and getattr(target, "room", None) is getattr(target_char, "room", None))
    if check == "istarget":
        return bool(target_char and getattr(mob, "mprog_target", None) is target_char)

    if len(tokens) < 2:
        return False

    value_token = tokens[1]

    if check == "affected":
        if target_char is None:
            return False
        try:
            flag = AffectFlag[value_token.upper()]
        except KeyError:
            return False
        if hasattr(target_char, "has_affect"):
            return target_char.has_affect(flag)
        affected_bits = int(getattr(target_char, "affected_by", 0) or 0)
        return bool(affected_bits & int(flag))

    if check == "act":
        if target_char is None:
            return False
        try:
            flag = ActFlag[value_token.upper()]
        except KeyError:
            return False
        combined = 0
        for source in (target_char, getattr(target_char, "prototype", None), getattr(target_char, "mob_index", None)):
            if source is None:
                continue
            raw = getattr(source, "act", 0)
            try:
                combined |= int(raw)
            except (TypeError, ValueError):
                continue
        return bool(combined & int(flag))
    if check == "off":
        if target_char is None:
            return False
        try:
            flag = OffFlag[value_token.upper()]
        except KeyError:
            return False
        combined = 0
        for source in (target_char, getattr(target_char, "prototype", None), getattr(target_char, "mob_index", None)):
            if source is None:
                continue
            raw = getattr(source, "off_flags", 0)
            try:
                combined |= int(raw)
            except (TypeError, ValueError):
                continue
        return bool(combined & int(flag))

    if check == "imm":
        if target_char is None:
            return False
        try:
            flag = ImmFlag[value_token.upper()]
        except KeyError:
            return False
        try:
            imm_bits = int(getattr(target_char, "imm_flags", 0) or 0)
        except (TypeError, ValueError):
            imm_bits = 0
        return bool(imm_bits & int(flag))

    if check == "carries":
        if target_char is None:
            return False
        if value_token.isdigit():
            return _character_has_item(target_char, vnum=int(value_token))
        return _character_has_item(target_char, name=value_token)

    if check == "wears":
        if target_char is None:
            return False
        if value_token.isdigit():
            return _character_has_item(target_char, vnum=int(value_token), require_worn=True)
        return _character_has_item(target_char, name=value_token, require_worn=True)

    if check == "has":
        if target_char is None:
            return False
        if value_token.isdigit():
            return _character_has_item(target_char, vnum=int(value_token))
        item_type = _lookup_item_type(value_token)
        if item_type is None:
            return False
        return _character_has_item(target_char, item_type=item_type)

    if check == "uses":
        if target_char is None:
            return False
        if value_token.isdigit():
            return _character_has_item(target_char, vnum=int(value_token), require_worn=True)
        item_type = _lookup_item_type(value_token)
        if item_type is None:
            return False
        return _character_has_item(target_char, item_type=item_type, require_worn=True)

    if check == "name":
        if code.lower() in {"o", "p"}:
            if target_obj is None:
                return False
            proto = getattr(target_obj, "prototype", None)
            return bool(
                proto
                and (
                    _match_name(getattr(proto, "name", None), value_token)
                    or _match_name(getattr(proto, "short_descr", None), value_token)
                )
            )
        if target_char is None:
            return False
        return bool(
            _match_name(getattr(target_char, "name", None), value_token)
            or _match_name(getattr(target_char, "short_descr", None), value_token)
        )

    if check in {"pos", "position"}:
        if target_char is None:
            return False
        try:
            expected = getattr(Position, value_token.upper())
        except AttributeError:
            return False
        return int(getattr(target_char, "position", Position.STANDING)) == int(expected)

    if check == "clan":
        if target_char is None:
            return False
        clan_value = getattr(target_char, "clan", 0)
        try:
            return int(clan_value or 0) == int(value_token)
        except ValueError:
            return str(clan_value).lower() == value_token.lower()

    if check == "race":
        if target_char is None:
            return False
        race_value = getattr(target_char, "race", 0)
        try:
            return int(race_value or 0) == int(value_token)
        except ValueError:
            return str(race_value).lower() == value_token.lower()

    if check == "class":
        if target_char is None:
            return False
        class_value = getattr(target_char, "ch_class", 0)
        try:
            return int(class_value or 0) == int(value_token)
        except ValueError:
            return str(class_value).lower() == value_token.lower()

    if check == "objtype":
        if target_obj is None:
            return False
        item_type = _lookup_item_type(value_token)
        if item_type is None:
            return False
        obj_type = _object_item_type(target_obj)
        return obj_type is not None and int(obj_type) == item_type

    if len(tokens) < 3:
        return False

    oper = tokens[1]
    try:
        rval = int(tokens[2])
    except ValueError:
        return False

    if check == "vnum":
        if code.lower() in {"o", "p"}:
            if target_obj is None:
                return False
            lval = _object_vnum(target_obj) or 0
        else:
            if target_char is None or not getattr(target_char, "is_npc", False):
                return False
            vnum = _character_proto_vnum(target_char)
            if vnum is None:
                return False
            lval = vnum
        return _compare_numbers(int(lval), oper, rval)

    if check == "hpcnt":
        if target_char is None:
            return False
        max_hit = max(1, int(getattr(target_char, "max_hit", 1)))
        current = int(getattr(target_char, "hit", max_hit))
        percent = current * 100 // max_hit
        return _compare_numbers(percent, oper, rval)

    if check == "room":
        target_room = getattr(target_char, "room", None) if target_char else None
        if target_room is None:
            return False
        vnum = getattr(target_room, "vnum", 0)
        return _compare_numbers(int(vnum or 0), oper, rval)

    if check == "sex":
        if target_char is None:
            return False
        return _compare_numbers(int(getattr(target_char, "sex", 0) or 0), oper, rval)

    if check == "level":
        if target_char is None:
            return False
        return _compare_numbers(int(getattr(target_char, "level", 0) or 0), oper, rval)

    if check == "align":
        if target_char is None:
            return False
        return _compare_numbers(int(getattr(target_char, "alignment", 0) or 0), oper, rval)

    if check == "money":
        if target_char is None:
            return False
        total = int(getattr(target_char, "gold", 0) or 0) + int(getattr(target_char, "silver", 0) or 0) * 100
        return _compare_numbers(total, oper, rval)

    if check.startswith("objval"):
        if target_obj is None:
            return False
        try:
            index = int(check[-1])
        except ValueError:
            return False
        values = getattr(target_obj, "value", []) or []
        if index >= len(values):
            proto = getattr(target_obj, "prototype", None)
            values = getattr(proto, "value", []) or []
        if index >= len(values):
            return False
        try:
            lval = int(values[index])
        except (TypeError, ValueError):
            return False
        return _compare_numbers(lval, oper, rval)

    if check == "grpsize":
        if target_char is None:
            return False
        size = _count_people_room(target_char, 4)
        return _compare_numbers(int(size), oper, rval)

    return False


def _split_control(line: str) -> tuple[str, str]:
    stripped = line.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(None, 1)
    control = parts[0]
    data = parts[1] if len(parts) > 1 else ""
    return control, data


def _execute_command(
    control: str,
    data: str,
    context: ProgramContext,
    mob: object,
    ch: object | None,
    arg1: object | None,
    arg2: object | None,
    rch: object | None,
) -> None:
    expanded = _expand_arg(data, mob, ch, arg1, arg2, rch)
    if control.lower() == "mob":
        sub_control, sub_args = _split_control(expanded)
        if not sub_control:
            return
        from mud import mob_cmds

        context.record(f"mob {sub_control}", sub_args, mob_command=True)
        had_context = hasattr(mob, "_mp_context")
        previous_context = getattr(mob, "_mp_context", None) if had_context else None
        mob._mp_context = context
        try:
            mob_cmds.mob_interpret(mob, expanded)
        finally:
            if had_context:
                mob._mp_context = previous_context
            elif hasattr(mob, "_mp_context"):
                delattr(mob, "_mp_context")
    else:
        from mud.commands import dispatcher

        command_line = control if not expanded else f"{control} {expanded}".strip()
        dispatcher.process_command(mob, command_line)
        context.record(control, expanded, mob_command=False)


def _program_flow(
    vnum: int,
    code: str,
    context: ProgramContext,
    mob: object,
    ch: object | None,
    arg1: object | None,
    arg2: object | None,
    rch: object | None,
) -> None:
    if not context.push():
        return
    try:
        state = [IN_BLOCK] * MAX_NESTED_LEVEL
        cond = [True] * MAX_NESTED_LEVEL
        level = 0
        for raw_line in code.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            control, data = _split_control(stripped)
            if not control:
                continue
            lower = control.lower()
            if lower == "if":
                if state[level] == BEGIN_BLOCK:
                    return
                state[level] = BEGIN_BLOCK
                level += 1
                if level >= MAX_NESTED_LEVEL:
                    return
                if level and not cond[level - 1]:
                    cond[level] = False
                    continue
                check_name, check_args = _split_control(data)
                cond[level] = _cmd_eval(check_name.lower(), check_args, mob, ch, arg1, arg2, rch)
                state[level] = END_BLOCK
            elif lower == "or":
                if not level or state[level - 1] != BEGIN_BLOCK:
                    return
                if level and not cond[level - 1]:
                    continue
                check_name, check_args = _split_control(data)
                result = _cmd_eval(check_name.lower(), check_args, mob, ch, arg1, arg2, rch)
                cond[level] = bool(cond[level] or result)
            elif lower == "and":
                if not level or state[level - 1] != BEGIN_BLOCK:
                    return
                if level and not cond[level - 1]:
                    continue
                check_name, check_args = _split_control(data)
                result = _cmd_eval(check_name.lower(), check_args, mob, ch, arg1, arg2, rch)
                cond[level] = bool(cond[level] and result)
            elif lower == "else":
                if not level or state[level - 1] != BEGIN_BLOCK:
                    return
                if level and not cond[level - 1]:
                    continue
                cond[level] = not cond[level]
            elif lower == "endif":
                if not level or state[level - 1] != BEGIN_BLOCK:
                    return
                cond[level] = True
                state[level] = IN_BLOCK
                level -= 1
                state[level] = END_BLOCK
            elif lower in {"break", "end"}:
                if not level or cond[level]:
                    return
            else:
                if level == 0 or cond[level]:
                    state[level] = IN_BLOCK
                    if getattr(mob, "mprog_target", None) is None and hasattr(ch, "is_npc"):
                        mob.mprog_target = ch
                    _execute_command(control, data, context, mob, ch, arg1, arg2, rch)
    finally:
        context.pop()


def _trigger_programs(
    mob: object,
    trigger: Trigger,
    *,
    actor: object | None = None,
    arg1: object | None = None,
    arg2: object | None = None,
    phrase: str | None = None,
    stop_after_first: bool = False,
) -> tuple[ProgramContext, bool]:
    context = ProgramContext(mob=mob)
    if not getattr(mob, "is_npc", False):
        return context, False
    programs = _get_programs(mob)
    fired = False
    for prog in programs:
        trig_type = int(getattr(prog, "trig_type", 0) or 0)
        if not trig_type & int(trigger):
            continue
        trig_phrase = getattr(prog, "trig_phrase", None)
        if phrase is not None and trig_phrase:
            haystack = str(phrase)
            needle = str(trig_phrase)
            if needle not in haystack:
                continue
        _register_program(prog)
        _program_flow(getattr(prog, "vnum", 0), getattr(prog, "code", ""), context, mob, actor, arg1, arg2, None)
        fired = True
        if stop_after_first:
            break
    return context, fired


def run_prog(
    mob: Character,
    trigger: Trigger,
    *,
    actor: object | None = None,
    arg1: object | None = None,
    arg2: object | None = None,
    phrase: str | None = None,
) -> list[ExecutionResult]:
    context, _ = _trigger_programs(
        mob,
        trigger,
        actor=actor,
        arg1=arg1,
        arg2=arg2,
        phrase=phrase,
        stop_after_first=False,
    )
    return context.results


def call_prog(
    vnum: int,
    mob: Character,
    actor: object | None = None,
    arg1: object | None = None,
    arg2: object | None = None,
    *,
    context: ProgramContext | None = None,
) -> list[ExecutionResult]:
    prog = _get_registered_program(vnum)
    if prog is None:
        for candidate in _get_programs(mob):
            if int(getattr(candidate, "vnum", 0) or 0) == int(vnum):
                _register_program(candidate)
                prog = candidate
                break
    if prog is None:
        return []
    exec_context = context or ProgramContext(mob=mob)
    _program_flow(
        getattr(prog, "vnum", 0),
        getattr(prog, "code", ""),
        exec_context,
        mob,
        actor,
        arg1,
        arg2,
        None,
    )
    return exec_context.results


def mp_act_trigger(
    argument: str,
    mob: Character,
    ch: object | None,
    arg1: object | None = None,
    arg2: object | None = None,
    trigger: Trigger = Trigger.ACT,
) -> bool:
    _, fired = _trigger_programs(
        mob,
        trigger,
        actor=ch,
        arg1=arg1,
        arg2=arg2,
        phrase=argument,
        stop_after_first=True,
    )
    return fired


def mp_percent_trigger(
    mob: Character,
    actor: object | None = None,
    arg1: object | None = None,
    arg2: object | None = None,
    trigger: Trigger = Trigger.RANDOM,
) -> bool:
    programs = _get_programs(mob)
    if not programs:
        return False
    context = ProgramContext(mob=mob)
    for prog in programs:
        trig_type = int(getattr(prog, "trig_type", 0) or 0)
        if not trig_type & int(trigger):
            continue
        trig_phrase = getattr(prog, "trig_phrase", "") or "0"
        try:
            percent = int(trig_phrase)
        except ValueError:
            percent = 0
        if rng_mm.number_percent() >= percent:
            continue
        _register_program(prog)
        _program_flow(
            getattr(prog, "vnum", 0),
            getattr(prog, "code", ""),
            context,
            mob,
            actor,
            arg1,
            arg2,
            None,
        )
        return True
    return False


def mp_bribe_trigger(mob: Character, ch: object | None, amount: int) -> bool:
    programs = _get_programs(mob)
    if not programs:
        return False
    context = ProgramContext(mob=mob)
    for prog in programs:
        if not int(getattr(prog, "trig_type", 0) or 0) & int(Trigger.BRIBE):
            continue
        trig_phrase = getattr(prog, "trig_phrase", "") or "0"
        try:
            threshold = int(trig_phrase)
        except ValueError:
            threshold = 0
        if amount < threshold:
            continue
        _register_program(prog)
        _program_flow(
            getattr(prog, "vnum", 0),
            getattr(prog, "code", ""),
            context,
            mob,
            ch,
            None,
            None,
            None,
        )
        return True
    return False


def mp_give_trigger(mob: Character, ch: object | None, obj: object | None) -> bool:
    programs = _get_programs(mob)
    if not programs or obj is None:
        return False
    name_tokens = str(getattr(obj, "name", "")).lower().split()
    context = ProgramContext(mob=mob)
    for prog in programs:
        if not int(getattr(prog, "trig_type", 0) or 0) & int(Trigger.GIVE):
            continue
        phrase = (getattr(prog, "trig_phrase", "") or "").strip()
        fire = False
        if phrase.isdigit():
            proto = getattr(obj, "prototype", None)
            if proto is None:
                proto = getattr(obj, "pIndexData", None)
            vnum = getattr(proto, "vnum", None)
            fire = vnum is not None and int(vnum) == int(phrase)
        else:
            needle = phrase.lower()
            fire = needle == "all" or any(token == needle for token in name_tokens)
        if not fire:
            continue
        _register_program(prog)
        _program_flow(
            getattr(prog, "vnum", 0),
            getattr(prog, "code", ""),
            context,
            mob,
            ch,
            obj,
            None,
            None,
        )
        return True
    return False


def mp_exit_trigger(ch: Character, direction: Direction) -> bool:
    room = getattr(ch, "room", None)
    if room is None:
        return False
    dir_value = int(getattr(direction, "value", direction))
    for mob in list(getattr(room, "people", [])):
        if mob is ch or not getattr(mob, "is_npc", False):
            continue
        programs = _get_programs(mob)
        if not programs:
            continue
        for prog in programs:
            trig_type = int(getattr(prog, "trig_type", 0) or 0)
            if not trig_type & (int(Trigger.EXIT) | int(Trigger.EXALL)):
                continue
            trig_phrase = getattr(prog, "trig_phrase", "") or ""
            try:
                trig_dir = int(trig_phrase) if trig_phrase else None
            except ValueError:
                trig_dir = None
            if trig_dir is not None and trig_dir != dir_value:
                continue
            if trig_type & int(Trigger.EXIT):
                default_pos = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
                if getattr(mob, "position", default_pos) != default_pos:
                    continue
                if not _can_see(mob, ch):
                    continue
            _register_program(prog)
            context = ProgramContext(mob=mob)
            _program_flow(
                getattr(prog, "vnum", 0),
                getattr(prog, "code", ""),
                context,
                mob,
                ch,
                None,
                None,
                None,
            )
            return True
    return False


def mp_greet_trigger(ch: Character) -> None:
    room = getattr(ch, "room", None)
    if room is None:
        return
    for mob in list(getattr(room, "people", [])):
        if mob is ch or not getattr(mob, "is_npc", False):
            continue
        programs = _get_programs(mob)
        if not programs:
            continue
        default_pos = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
        if any(int(getattr(prog, "trig_type", 0) or 0) & int(Trigger.GREET) for prog in programs):
            if getattr(mob, "position", default_pos) == default_pos and _can_see(mob, ch):
                if mp_percent_trigger(mob, ch, trigger=Trigger.GREET):
                    continue
        if any(int(getattr(prog, "trig_type", 0) or 0) & int(Trigger.GRALL) for prog in programs):
            mp_percent_trigger(mob, ch, trigger=Trigger.GRALL)


def mp_hprct_trigger(mob: Character, ch: object | None) -> bool:
    programs = _get_programs(mob)
    if not programs:
        return False
    context = ProgramContext(mob=mob)
    for prog in programs:
        if not int(getattr(prog, "trig_type", 0) or 0) & int(Trigger.HPCNT):
            continue
        trig_phrase = getattr(prog, "trig_phrase", "") or "0"
        try:
            threshold = int(trig_phrase)
        except ValueError:
            continue
        max_hit = max(1, int(getattr(mob, "max_hit", 1)))
        current = int(getattr(mob, "hit", max_hit))
        percent = current * 100 // max_hit
        if percent >= threshold:
            continue
        _register_program(prog)
        _program_flow(
            getattr(prog, "vnum", 0),
            getattr(prog, "code", ""),
            context,
            mob,
            ch,
            None,
            None,
            None,
        )
        return True
    return False


def mp_random_trigger(mob: Character) -> bool:
    return mp_percent_trigger(mob, trigger=Trigger.RANDOM)


def mp_delay_trigger(mob: Character) -> bool:
    delay = int(getattr(mob, "mprog_delay", 0) or 0)
    if delay <= 0:
        return False
    delay -= 1
    mob.mprog_delay = delay
    if delay > 0:
        return False
    mob.mprog_delay = 0
    return mp_percent_trigger(mob, trigger=Trigger.DELAY)


def mp_speech_trigger(argument: str, mob: Character, ch: object | None) -> bool:
    return mp_act_trigger(argument, mob, ch, trigger=Trigger.SPEECH)


def mp_fight_trigger(mob: Character, ch: object | None) -> bool:
    return mp_percent_trigger(mob, ch, trigger=Trigger.FIGHT)


def mp_death_trigger(mob: Character, ch: object | None) -> bool:
    return mp_percent_trigger(mob, ch, trigger=Trigger.DEATH)


def mp_kill_trigger(mob: Character, ch: object | None) -> bool:
    return mp_percent_trigger(mob, ch, trigger=Trigger.KILL)


def mp_surr_trigger(mob: Character, ch: object | None) -> bool:
    return mp_percent_trigger(mob, ch, trigger=Trigger.SURR)


# ============================================================================
# MobProg Helper Functions (ROM parity)
# ============================================================================
# The following functions provide public API matching ROM C mob_prog.c
# They wrap internal helper functions with ROM-compatible signatures.


def count_people_room(mob: Character, flag: int = 0) -> int:
    """Count characters in mob's room based on filter flag.

    ROM parity: src/mob_prog.c:263-279 count_people_room

    Args:
        mob: The mob whose room to check
        flag: Filter type:
            0 = all visible characters (excluding mob itself)
            1 = players only
            2 = NPCs only
            3 = NPCs with same vnum as mob
            4 = same group members

    Returns:
        Number of characters matching the filter criteria
    """
    return _count_people_room(mob, flag)


def keyword_lookup(table: list[str], keyword: str) -> int:
    """Return index of keyword in table, or -1 if not found.

    ROM parity: src/mob_prog.c:199-206 keyword_lookup

    Args:
        table: List of strings to search (ROM uses null-terminated array)
        keyword: String to find (case-insensitive)

    Returns:
        Index of keyword in table, or -1 if not found

    Note:
        ROM C uses table[i][0] != '\\n' as terminator.
        Python equivalent checks list bounds and empty strings.
    """
    if not keyword or not table:
        return -1
    lowered = keyword.lower()
    for i, entry in enumerate(table):
        if not entry or entry.startswith("\n"):
            break
        if entry.lower() == lowered:
            return i
    return -1


def has_item(char: Character, vnum: int = -1, item_type: int = -1, require_worn: bool = False) -> bool:
    """Check if character has item matching vnum or item_type.

    ROM parity: src/mob_prog.c:309-318 has_item

    Args:
        char: Character to check
        vnum: Item vnum to match (-1 = any)
        item_type: Item type to match (-1 = any)
        require_worn: If True, item must be equipped

    Returns:
        True if character has matching item

    Note:
        At least one of vnum or item_type must be specified (not -1).
        If both specified, item must match both criteria.
    """
    if char is None:
        return False

    vnum_filter = None if vnum < 0 else vnum
    type_filter = None if item_type < 0 else item_type

    return _character_has_item(char, vnum=vnum_filter, item_type=type_filter, require_worn=require_worn)


def get_mob_vnum_room(char: Character, vnum: int) -> bool:
    """Check if mob with given vnum exists in character's room.

    ROM parity: src/mob_prog.c:323-330 get_mob_vnum_room

    Args:
        char: Character whose room to check
        vnum: Mob prototype vnum to find

    Returns:
        True if mob with matching vnum found in room
    """
    room = getattr(char, "room", None)
    if room is None:
        return False

    for occupant in getattr(room, "people", []) or []:
        if occupant is char:
            continue
        if not getattr(occupant, "is_npc", False):
            continue
        if _character_proto_vnum(occupant) == vnum:
            return True

    return False


def get_obj_vnum_room(char: Character, vnum: int) -> bool:
    """Check if object with given vnum exists in character's room.

    ROM parity: src/mob_prog.c:335-342 get_obj_vnum_room

    Args:
        char: Character whose room to check
        vnum: Object prototype vnum to find

    Returns:
        True if object with matching vnum found in room
    """
    room = getattr(char, "room", None)
    if room is None:
        return False

    for obj in getattr(room, "contents", []) or []:
        if _object_vnum(obj) == vnum:
            return True

    return False
