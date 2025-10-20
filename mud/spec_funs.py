from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mud.combat import multi_hit
from mud.combat.engine import stop_fighting
from mud.models.constants import (
    LEVEL_IMMORTAL,
    OBJ_VNUM_WHISTLE,
    GROUP_VNUM_OGRES,
    GROUP_VNUM_TROLLS,
    MOB_VNUM_PATROLMAN,
    AffectFlag,
    CommFlag,
    Direction,
    EX_CLOSED,
    ItemType,
    PlayerFlag,
    Position,
    WearFlag,
    convert_flags_from_letters,
)
from mud.registry import room_registry
from mud.skills.registry import skill_registry as global_skill_registry
from mud.utils import rng_mm
from mud.utils.act import act_format
from mud.world.vision import can_see_character
from mud.time import time_info
from mud.world.movement import move_character

try:  # Import optional helper used by janitors to respect loot restrictions.
    from mud.ai import _can_loot as _can_loot_item
except Exception:  # pragma: no cover - fallback when AI helpers unavailable
    def _can_loot_item(_mob: Any, _obj: Any) -> bool:
        return True

spec_fun_registry: dict[str, Callable[..., Any]] = {}

_DIRECTION_NAMES = [
    "north",
    "east",
    "south",
    "west",
    "up",
    "down",
]


def register_spec_fun(name: str, func: Callable[..., Any]) -> None:
    """Register *func* under *name*, storing key in lowercase."""
    spec_fun_registry[name.lower()] = func


def get_spec_fun(name: str) -> Callable[..., Any] | None:
    """Return a spec_fun for *name* using case-insensitive lookup."""
    return spec_fun_registry.get(name.lower())


def run_npc_specs() -> None:
    """Invoke registered spec_funs for NPCs in all rooms.

    For each NPC (MobInstance) present in any room, if its prototype has a
    non-empty ``spec_fun`` name and a function is registered under that name,
    call it with the mob instance.
    """
    from mud.registry import room_registry

    for room in list(room_registry.values()):
        for entity in list(getattr(room, "people", [])):
            spec_attr = getattr(entity, "spec_fun", None)
            func = None

            if callable(spec_attr):
                func = spec_attr
            elif isinstance(spec_attr, str) and spec_attr:
                func = get_spec_fun(spec_attr)

            if func is None:
                proto = getattr(entity, "prototype", None)
                proto_spec = getattr(proto, "spec_fun", None)
                if callable(proto_spec):
                    func = proto_spec
                elif isinstance(proto_spec, str) and proto_spec:
                    func = get_spec_fun(proto_spec)

            if func is None:
                continue

            try:
                func(entity)
            except Exception:
                # Spec fun failures must not break the tick loop
                continue


def _get_position(ch: Any) -> Position:
    try:
        value = int(getattr(ch, "position", Position.STANDING))
    except Exception:
        value = int(Position.STANDING)
    try:
        return Position(value)
    except ValueError:
        return Position.STANDING


def _is_awake(ch: Any) -> bool:
    return _get_position(ch) > Position.SLEEPING


def _has_affect(ch: Any, flag: AffectFlag) -> bool:
    checker = getattr(ch, "has_affect", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:
            return False
    affected = getattr(ch, "affected_by", 0)
    try:
        return bool(int(affected) & int(flag))
    except Exception:
        return False


def _append_message(target: Any, message: str) -> None:
    inbox = getattr(target, "messages", None)
    if isinstance(inbox, list):
        inbox.append(message)


def _broadcast_room_message(room: Any, template: str | None, actor: Any, victim: Any | None) -> None:
    if not template:
        return
    for listener in _room_occupants(room):
        formatted = act_format(template, recipient=listener, actor=actor, arg2=victim)
        if formatted:
            _append_message(listener, formatted)


_MAYOR_OPEN_PATH = "W3a3003b33000c111d0d111Oe333333Oe22c222112212111a1S."
_MAYOR_CLOSE_PATH = "W3a3003b33000c111d0d111CE333333CE22c222112212111a1S."
_MAYOR_DIRECTION_NAMES: dict[str, Direction] = {
    "0": Direction.NORTH,
    "1": Direction.EAST,
    "2": Direction.SOUTH,
    "3": Direction.WEST,
}
_MAYOR_OPPOSITE: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}
_mayor_path: str | None = None
_mayor_index = 0
_mayor_moving = False


def _reset_spec_mayor_state() -> None:
    """Reset cached mayor path state (useful for tests)."""

    global _mayor_path, _mayor_index, _mayor_moving
    _mayor_path = None
    _mayor_index = 0
    _mayor_moving = False


def _mayor_emit(mayor: Any, message: str) -> None:
    room = getattr(mayor, "room", None)
    if room is None:
        return
    for occupant in _room_occupants(room):
        if occupant is mayor:
            continue
        formatted = act_format(message, recipient=occupant, actor=mayor)
        if formatted:
            _append_message(occupant, formatted)


def _mayor_move(mayor: Any, direction_token: str) -> bool:
    room = getattr(mayor, "room", None)
    if room is None:
        return False

    direction = _MAYOR_DIRECTION_NAMES.get(direction_token)
    if direction is None:
        return False

    exits = getattr(room, "exits", None)
    if not isinstance(exits, list):
        return False

    index = int(direction)
    if index >= len(exits):
        return False

    exit_obj = exits[index]
    to_room = getattr(exit_obj, "to_room", None) if exit_obj is not None else None
    if to_room is None:
        return False

    exit_flags = getattr(exit_obj, "exit_info", 0) if exit_obj is not None else 0
    if exit_flags & EX_CLOSED:
        return False

    if hasattr(room, "people") and isinstance(room.people, list) and mayor in room.people:
        room.people.remove(mayor)
    if hasattr(to_room, "people") and isinstance(to_room.people, list):
        if mayor not in to_room.people:
            to_room.people.append(mayor)
    mayor.room = to_room
    return True


def _mayor_toggle_gate(mayor: Any, *, open_gate: bool) -> None:
    room = getattr(mayor, "room", None)
    if room is None:
        return

    exits = getattr(room, "exits", None)
    if not isinstance(exits, list):
        return

    target_index: int | None = None
    target_exit = None
    for idx, exit_obj in enumerate(exits):
        if exit_obj is None:
            continue
        keyword = (getattr(exit_obj, "keyword", "") or "").lower()
        if "gate" in keyword:
            target_index = idx
            target_exit = exit_obj
            break

    if target_exit is None or target_index is None:
        return

    if open_gate:
        target_exit.exit_info &= ~EX_CLOSED
    else:
        target_exit.exit_info |= EX_CLOSED

    try:
        direction = Direction(target_index)
    except ValueError:
        direction = None

    if direction is not None:
        opposite = _MAYOR_OPPOSITE.get(direction)
        if opposite is not None:
            to_room = getattr(target_exit, "to_room", None)
            if to_room is not None:
                exits_rev = getattr(to_room, "exits", None)
                if isinstance(exits_rev, list) and int(opposite) < len(exits_rev):
                    reverse_exit = exits_rev[int(opposite)]
                    if reverse_exit is not None:
                        if open_gate:
                            reverse_exit.exit_info &= ~EX_CLOSED
                        else:
                            reverse_exit.exit_info |= EX_CLOSED

def _clear_comm_flag(ch: Any, flag: CommFlag) -> None:
    try:
        current = int(getattr(ch, "comm", 0) or 0)
    except Exception:
        current = 0
    ch.comm = current & ~int(flag)


def _spec_name(ch: Any) -> str | None:
    spec_attr = getattr(ch, "spec_fun", None)
    if isinstance(spec_attr, str) and spec_attr:
        return spec_attr.lower()
    proto = getattr(ch, "prototype", None)
    proto_spec = getattr(proto, "spec_fun", None)
    if isinstance(proto_spec, str) and proto_spec:
        return proto_spec.lower()
    return None


def _display_name(ch: Any) -> str:
    name = getattr(ch, "name", None) or getattr(ch, "short_descr", None)
    if not name:
        proto = getattr(ch, "prototype", None)
        name = getattr(proto, "short_descr", None) or getattr(proto, "player_name", None)
    return str(name or "Someone")


def _has_player_flag(ch: Any, flag: PlayerFlag) -> bool:
    act = getattr(ch, "act", 0)
    try:
        return bool(int(act) & int(flag))
    except Exception:
        return False


def _prototype_vnum(entity: Any) -> int | None:
    proto = getattr(entity, "prototype", None)
    vnum = getattr(proto, "vnum", None)
    if vnum is None:
        vnum = getattr(entity, "vnum", None)
    try:
        return int(vnum) if vnum is not None else None
    except Exception:
        return None


def _prototype_group(entity: Any) -> int:
    proto = getattr(entity, "prototype", None)
    group = getattr(proto, "group", None)
    if group is None:
        group = getattr(entity, "group", 0)
    try:
        return int(group)
    except Exception:
        return 0


def _room_occupants(room: Any) -> list[Any]:
    people = getattr(room, "people", [])
    return list(people) if isinstance(people, list) else list(people or [])


def _room_objects(room: Any) -> list[Any]:
    contents = getattr(room, "contents", None)
    if isinstance(contents, list):
        return list(contents)
    if contents is None:
        return []
    try:
        return list(contents)
    except Exception:
        return []


def _object_wear_flags(obj: Any) -> int:
    raw = getattr(obj, "wear_flags", None)
    if raw is None:
        proto = getattr(obj, "prototype", None)
        if proto is not None and proto is not obj:
            return _object_wear_flags(proto)
        return 0
    if isinstance(raw, WearFlag):
        return int(raw)
    try:
        return int(raw)
    except Exception:
        if isinstance(raw, str):
            try:
                return int(convert_flags_from_letters(raw, WearFlag))
            except Exception:
                return 0
    return 0


def _object_item_type(obj: Any) -> ItemType | None:
    raw = getattr(obj, "item_type", None)
    if raw is None:
        proto = getattr(obj, "prototype", None)
        if proto is not None and proto is not obj:
            return _object_item_type(proto)
        return None
    if isinstance(raw, ItemType):
        return raw
    try:
        return ItemType(int(raw))
    except Exception:
        if isinstance(raw, str):
            return ItemType.__members__.get(raw.upper())
    return None


def _object_cost(obj: Any) -> int:
    value = getattr(obj, "cost", None)
    if value is None:
        proto = getattr(obj, "prototype", None)
        if proto is not None and proto is not obj:
            return _object_cost(proto)
        return 0
    try:
        return int(value)
    except Exception:
        return 0


def _object_is_takeable(obj: Any) -> bool:
    try:
        return bool(_object_wear_flags(obj) & int(WearFlag.TAKE))
    except Exception:
        return False


def _move_object_to_mob(obj: Any, mob: Any, room: Any) -> None:
    contents = getattr(room, "contents", None)
    if isinstance(contents, list) and obj in contents:
        contents.remove(obj)
    if hasattr(room, "remove_object"):
        try:
            room.remove_object(obj)  # type: ignore[attr-defined]
        except Exception:
            pass

    if hasattr(obj, "in_room"):
        obj.in_room = None
    if hasattr(obj, "location"):
        obj.location = None
    if hasattr(obj, "in_obj"):
        obj.in_obj = None

    inventory = getattr(mob, "inventory", None)
    if isinstance(inventory, list) and obj not in inventory:
        inventory.append(obj)
    if hasattr(obj, "carried_by"):
        obj.carried_by = mob

    pickup_text = "$n picks up some trash."
    for occupant in _room_occupants(room):
        if occupant is mob:
            continue
        message = act_format(pickup_text, recipient=occupant, actor=mob, arg2=obj)
        if message:
            _append_message(occupant, message)


def spec_breath_any(mob: Any) -> bool:
    if _get_position(mob) != Position.FIGHTING:
        return False

    roll = rng_mm.number_bits(3)
    if roll == 0:
        return spec_breath_fire(mob)
    if roll in (1, 2):
        return spec_breath_lightning(mob)
    if roll == 3:
        return spec_breath_gas(mob)
    if roll == 4:
        return spec_breath_acid(mob)
    return spec_breath_frost(mob)


def spec_breath_acid(mob: Any) -> bool:
    return _dragon_breath(mob, "acid breath")


def spec_breath_fire(mob: Any) -> bool:
    return _dragon_breath(mob, "fire breath")


def spec_breath_frost(mob: Any) -> bool:
    return _dragon_breath(mob, "frost breath")


def spec_breath_gas(mob: Any) -> bool:
    if _get_position(mob) != Position.FIGHTING:
        return False
    return _cast_spell(mob, None, "gas breath")


def spec_breath_lightning(mob: Any) -> bool:
    return _dragon_breath(mob, "lightning breath")


def spec_mayor(mob: Any) -> bool:
    global _mayor_path, _mayor_index, _mayor_moving

    if mob is None:
        return False

    if not _mayor_moving:
        if time_info.hour == 6:
            _mayor_path = _MAYOR_OPEN_PATH
            _mayor_index = 0
            _mayor_moving = True
        elif time_info.hour == 20:
            _mayor_path = _MAYOR_CLOSE_PATH
            _mayor_index = 0
            _mayor_moving = True

    if getattr(mob, "fighting", None):
        return spec_cast_mage(mob)

    if not _mayor_moving or _mayor_path is None:
        return False

    if _get_position(mob) < Position.SLEEPING:
        return False

    if _mayor_index >= len(_mayor_path):
        _mayor_moving = False
        _mayor_path = None
        _mayor_index = 0
        return False

    action = _mayor_path[_mayor_index]
    _mayor_index += 1

    if action in _MAYOR_DIRECTION_NAMES:
        return _mayor_move(mob, action)

    if action == "W":
        mob.position = int(Position.STANDING)
        _mayor_emit(mob, "$n awakens and groans loudly.")
        return True

    if action == "S":
        mob.position = int(Position.SLEEPING)
        _mayor_emit(mob, "$n lies down and falls asleep.")
        return True

    if action == "a":
        _mayor_emit(mob, "$n says 'Hello Honey!'")
        return True

    if action == "b":
        _mayor_emit(
            mob,
            "$n says 'What a view!  I must do something about that dump!'",
        )
        return True

    if action == "c":
        _mayor_emit(
            mob,
            "$n says 'Vandals!  Youngsters have no respect for anything!'",
        )
        return True

    if action == "d":
        _mayor_emit(mob, "$n says 'Good day, citizens!'")
        return True

    if action == "e":
        _mayor_emit(mob, "$n says 'I hereby declare the city of Midgaard open!'")
        return True

    if action == "E":
        _mayor_emit(mob, "$n says 'I hereby declare the city of Midgaard closed!'")
        return True

    if action == "O":
        _mayor_toggle_gate(mob, open_gate=True)
        _mayor_emit(mob, "$n opens the city gate.")
        return True

    if action == "C":
        _mayor_toggle_gate(mob, open_gate=False)
        _mayor_emit(mob, "$n closes the city gate.")
        return True

    if action == ".":
        _mayor_moving = False
        _mayor_path = None
        _mayor_index = 0
        return False

    return False


def spec_janitor(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob):
        return False

    for obj in _room_objects(room):
        if not _object_is_takeable(obj):
            continue
        if not _can_loot_item(mob, obj):
            continue

        item_type = _object_item_type(obj)
        cost = _object_cost(obj)
        if item_type in (ItemType.DRINK_CON, ItemType.TRASH) or cost < 10:
            _move_object_to_mob(obj, mob, room)
            return True

    return False


def _drop_object_into_room(obj: Any, room: Any) -> None:
    if hasattr(obj, "carried_by"):
        obj.carried_by = None
    if hasattr(obj, "in_obj"):
        obj.in_obj = None
    if hasattr(obj, "in_room"):
        obj.in_room = room
    if hasattr(obj, "location"):
        obj.location = room

    if hasattr(room, "add_object"):
        room.add_object(obj)
    else:
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and obj not in contents:
            contents.append(obj)


def _remove_corpse_from_room(corpse: Any, room: Any) -> None:
    if hasattr(room, "contents") and isinstance(room.contents, list):
        if corpse in room.contents:
            room.contents.remove(corpse)
    if hasattr(room, "remove_object"):
        try:
            room.remove_object(corpse)  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(corpse, "in_room"):
        corpse.in_room = None
    if hasattr(corpse, "location"):
        corpse.location = None


def _corpse_contents(corpse: Any) -> list[Any]:
    contents: list[Any] = []
    seen: set[int] = set()
    for attr in ("contained_items", "contains"):
        value = getattr(corpse, attr, None)
        if not isinstance(value, list):
            continue
        for item in value:
            key = id(item)
            if key in seen:
                continue
            seen.add(key)
            contents.append(item)
    return contents


def _clear_corpse_contents(corpse: Any, item: Any) -> None:
    for attr in ("contained_items", "contains"):
        value = getattr(corpse, attr, None)
        if isinstance(value, list):
            while item in value:
                value.remove(item)


def spec_fido(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob):
        return False

    for corpse in _room_objects(room):
        if _object_item_type(corpse) is not ItemType.CORPSE_NPC:
            continue

        message = "$n savagely devours a corpse."
        for occupant in _room_occupants(room):
            if occupant is mob:
                continue
            formatted = act_format(message, recipient=occupant, actor=mob, arg2=corpse)
            if formatted:
                _append_message(occupant, formatted)

        for item in _corpse_contents(corpse):
            _clear_corpse_contents(corpse, item)
            _drop_object_into_room(item, room)

        _remove_corpse_from_room(corpse, room)
        return True

    return False


def spec_poison(mob: Any) -> bool:
    if _get_position(mob) != Position.FIGHTING:
        return False

    victim = getattr(mob, "fighting", None)
    if victim is None:
        return False

    try:
        level = max(int(getattr(mob, "level", 0) or 0), 0)
    except Exception:
        level = 0

    if rng_mm.number_percent() > 2 * level:
        return False

    bite_self = act_format("You bite $N!", recipient=mob, actor=mob, arg2=victim)
    if bite_self:
        _append_message(mob, bite_self)

    for occupant in _room_occupants(getattr(mob, "room", None)):
        if occupant is mob or occupant is victim:
            continue
        broadcast = act_format("$n bites $N!", recipient=occupant, actor=mob, arg2=victim)
        if broadcast:
            _append_message(occupant, broadcast)

    bite_victim = act_format("$n bites you!", recipient=victim, actor=mob, arg2=victim)
    if bite_victim:
        _append_message(victim, bite_victim)

    _cast_spell(mob, victim, "poison")
    return True


def _find_fighting_victim(mob: Any) -> Any | None:
    if _get_position(mob) != Position.FIGHTING:
        return None
    room = getattr(mob, "room", None)
    if room is None:
        return None
    fallback = None
    for occupant in _room_occupants(room):
        if getattr(occupant, "fighting", None) is mob and rng_mm.number_bits(2) == 0:
            return occupant
        if getattr(occupant, "fighting", None) is mob and fallback is None:
            fallback = occupant
    return fallback


def _find_breath_victim(mob: Any) -> Any | None:
    if _get_position(mob) != Position.FIGHTING:
        return None

    room = getattr(mob, "room", None)
    if room is None:
        return None

    fallback = None
    for occupant in _room_occupants(room):
        if getattr(occupant, "fighting", None) is not mob:
            continue
        if rng_mm.number_bits(3) == 0:
            return occupant
        if fallback is None:
            fallback = occupant
    return fallback


def _dragon_breath(mob: Any, spell_name: str) -> bool:
    victim = _find_breath_victim(mob)
    if victim is None:
        return False
    return _cast_spell(mob, victim, spell_name)


def _get_skill_registry():
    try:  # Local import avoids circular dependency during initialization
        from mud.world import world_state  # type: ignore
    except Exception:  # pragma: no cover - defensive
        world_state = None  # type: ignore

    registry = None
    if world_state is not None:  # type: ignore[truthy-bool]
        registry = getattr(world_state, "skill_registry", None)
    if registry is None:
        registry = global_skill_registry
    return registry


def _cast_spell(caster: Any, target: Any, spell_name: str) -> bool:
    registry = _get_skill_registry()
    if registry is None:
        return False
    skill = registry.find_spell(caster, spell_name) if hasattr(registry, "find_spell") else None
    handler = None
    if skill is not None:
        handler = registry.handlers.get(skill.name)
    if handler is None:
        handler = registry.handlers.get(spell_name)
    if handler is None:
        return False
    handler(caster, target)
    return True


def _select_spell(mob: Any, table: dict[int, tuple[int, str]], default: tuple[int, str]) -> str:
    level = int(getattr(mob, "level", 0) or 0)
    while True:
        roll = rng_mm.number_bits(4)
        min_level, spell = table.get(roll, default)
        if level >= min_level:
            return spell


def _equipped_items(mob: Any) -> list[Any]:
    equipment = getattr(mob, "equipment", None)
    if isinstance(equipment, dict):
        return [item for item in equipment.values() if item is not None]
    return []


def _find_whistle(mob: Any) -> Any | None:
    for item in _equipped_items(mob):
        proto = getattr(item, "prototype", None)
        vnum = getattr(proto, "vnum", None)
        if vnum == OBJ_VNUM_WHISTLE:
            return item
    return None


def _broadcast_area(room: Any, message: str) -> None:
    area = getattr(room, "area", None)
    if area is None:
        return
    for other_room in list(room_registry.values()):
        if other_room is room:
            continue
        if getattr(other_room, "area", None) is area:
            other_room.broadcast(message)


def _broadcast_room(mob: Any, message: str) -> None:
    room = getattr(mob, "room", None)
    if room is None:
        return
    for occupant in _room_occupants(room):
        if occupant is mob:
            continue
        formatted = act_format(message, recipient=occupant, actor=mob)
        if formatted:
            _append_message(occupant, formatted)


def _attack(mob: Any, victim: Any) -> None:
    multi_hit(mob, victim)


def _issue_command(mob: Any, command: Callable[[Any, str], Any] | str, argument: str) -> Any:
    func: Callable[[Any, str], Any] | None
    if isinstance(command, str):
        try:
            from mud.commands import combat as combat_commands
        except Exception:
            func = None
        else:
            func = getattr(combat_commands, command, None)
    else:
        func = command

    if func is None:
        return ""

    try:
        return func(mob, argument)
    except Exception:
        return ""


def _nasty_try_flee(mob: Any) -> bool:
    victim = getattr(mob, "fighting", None)
    if victim is None:
        return False

    room = getattr(mob, "room", None)
    if room is None:
        stop_fighting(mob, True)
        return False

    exits = list(getattr(room, "exits", []) or [])
    if not exits:
        return False

    for _ in range(6):
        door = rng_mm.number_bits(3)
        if door >= len(_DIRECTION_NAMES) or door >= len(exits):
            continue
        exit_obj = exits[door]
        if exit_obj is None:
            continue
        if getattr(exit_obj, "exit_info", 0) & int(EX_CLOSED):
            continue
        if getattr(exit_obj, "to_room", None) is None:
            continue

        previous_room = room
        move_character(mob, _DIRECTION_NAMES[door])
        if getattr(mob, "room", None) is previous_room:
            continue

        for observer in _room_occupants(previous_room):
            if observer is mob:
                continue
            flee_message = act_format("$n has fled!", recipient=observer, actor=mob)
            if flee_message:
                _append_message(observer, flee_message)

        if not getattr(mob, "is_npc", True):
            _append_message(mob, "You flee from combat!")

        stop_fighting(mob, True)
        return True

    return False


def spec_nasty(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob):
        return False

    fighting = getattr(mob, "fighting", None)
    if fighting is None:
        mob_level = int(getattr(mob, "level", 0) or 0)
        for victim in _room_occupants(room):
            if getattr(victim, "is_npc", False):
                continue
            victim_level = int(getattr(victim, "level", 0) or 0)
            if victim_level <= mob_level or victim_level >= mob_level + 10:
                continue
            target_name = getattr(victim, "name", "") or ""
            _issue_command(mob, "do_backstab", target_name)
            if getattr(mob, "fighting", None) is None:
                _issue_command(mob, "do_kill", target_name)
            return True
        return False

    roll = rng_mm.number_bits(2)
    if roll == 0:
        victim = fighting
        gold_before = int(getattr(victim, "gold", 0) or 0)
        stolen = gold_before // 10
        if stolen:
            setattr(victim, "gold", gold_before - stolen)
            mob_gold = int(getattr(mob, "gold", 0) or 0)
            setattr(mob, "gold", mob_gold + stolen)

        victim_message = act_format(
            "$n rips apart your coin purse, spilling your gold!",
            recipient=victim,
            actor=mob,
            arg2=victim,
        )
        mob_message = act_format(
            "You slash apart $N's coin purse and gather his gold.",
            recipient=mob,
            actor=mob,
            arg2=victim,
        )

        if victim_message:
            _append_message(victim, victim_message)
        if mob_message:
            _append_message(mob, mob_message)

        for observer in _room_occupants(room):
            if observer is mob or observer is victim:
                continue
            observe_message = act_format(
                "$N's coin purse is ripped apart!",
                recipient=observer,
                actor=mob,
                arg2=victim,
            )
            if observe_message:
                _append_message(observer, observe_message)

        return True

    if roll == 1:
        _nasty_try_flee(mob)
        return True

    return False


def spec_thief(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or _get_position(mob) != Position.STANDING:
        return False

    mob_level = max(int(getattr(mob, "level", 0) or 0), 0)
    for victim in _room_occupants(room):
        if getattr(victim, "is_npc", False):
            continue
        victim_level = int(getattr(victim, "level", 0) or 0)
        if victim_level >= LEVEL_IMMORTAL:
            continue
        if rng_mm.number_bits(5) != 0:
            continue
        if not can_see_character(mob, victim):
            continue

        if _is_awake(victim):
            if rng_mm.number_range(0, mob_level) == 0:
                victim_message = act_format(
                    "You discover $n's hands in your wallet!",
                    recipient=victim,
                    actor=mob,
                    arg2=victim,
                )
                _append_message(victim, victim_message)
                for observer in _room_occupants(room):
                    if observer is victim or observer is mob:
                        continue
                    alert = act_format(
                        "$N discovers $n's hands in $S wallet!",
                        recipient=observer,
                        actor=mob,
                        arg2=victim,
                    )
                    _append_message(observer, alert)
                return True
            continue

        percent_cap = max(mob_level // 2, 0)
        steal_cap = mob_level * mob_level

        percent_gold = min(rng_mm.number_range(1, 20), percent_cap)
        victim_gold = int(getattr(victim, "gold", 0) or 0)
        gold = (victim_gold * percent_gold) // 100
        gold = min(gold, steal_cap * 10)
        if gold:
            setattr(victim, "gold", victim_gold - gold)
            mob_gold = int(getattr(mob, "gold", 0) or 0)
            setattr(mob, "gold", mob_gold + gold)

        percent_silver = min(rng_mm.number_range(1, 20), percent_cap)
        victim_silver = int(getattr(victim, "silver", 0) or 0)
        silver = (victim_silver * percent_silver) // 100
        silver = min(silver, steal_cap * 25)
        if silver:
            setattr(victim, "silver", victim_silver - silver)
            mob_silver = int(getattr(mob, "silver", 0) or 0)
            setattr(mob, "silver", mob_silver + silver)

        return True

    return False


# --- Minimal ROM-like spec functions (rng_mm parity) ---


def spec_cast_adept(mob: Any) -> bool:
    if not _is_awake(mob):
        return False

    room = getattr(mob, "room", None)
    if room is None:
        return False

    victim = None
    for occupant in _room_occupants(room):
        if occupant is mob:
            continue
        if getattr(occupant, "is_npc", False):
            continue
        if not can_see_character(mob, occupant):
            continue
        level = int(getattr(occupant, "level", 0) or 0)
        if level >= 11:
            continue
        if rng_mm.number_bits(1) != 0:
            continue
        victim = occupant
        break

    if victim is None:
        return False

    roll = rng_mm.number_bits(4)
    if roll == 0:
        _broadcast_room(mob, "$n utters the word 'abrazak'.")
        _cast_spell(mob, victim, "armor")
        return True
    if roll == 1:
        _broadcast_room(mob, "$n utters the word 'fido'.")
        _cast_spell(mob, victim, "bless")
        return True
    if roll == 2:
        _broadcast_room(mob, "$n utters the words 'judicandus noselacri'.")
        _cast_spell(mob, victim, "cure blindness")
        return True
    if roll == 3:
        _broadcast_room(mob, "$n utters the words 'judicandus dies'.")
        _cast_spell(mob, victim, "cure light")
        return True
    if roll == 4:
        _broadcast_room(mob, "$n utters the words 'judicandus sausabru'.")
        _cast_spell(mob, victim, "cure poison")
        return True
    if roll == 5:
        _broadcast_room(mob, "$n utters the word 'candusima'.")
        _cast_spell(mob, victim, "refresh")
        return True
    if roll == 6:
        _broadcast_room(mob, "$n utters the words 'judicandus eugzagz'.")
        _cast_spell(mob, victim, "cure disease")
        return True

    return False


# Convenience registration name matching ROM conventions
register_spec_fun("spec_breath_any", spec_breath_any)
register_spec_fun("spec_breath_acid", spec_breath_acid)
register_spec_fun("spec_breath_fire", spec_breath_fire)
register_spec_fun("spec_breath_frost", spec_breath_frost)
register_spec_fun("spec_breath_gas", spec_breath_gas)
register_spec_fun("spec_breath_lightning", spec_breath_lightning)
register_spec_fun("spec_cast_adept", spec_cast_adept)


# --- Justice system special functions ---


def spec_executioner(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob) or getattr(mob, "fighting", None) is not None:
        return False

    target = None
    crime = ""
    for occupant in _room_occupants(room):
        if getattr(occupant, "is_npc", False):
            continue
        if _has_player_flag(occupant, PlayerFlag.KILLER) and can_see_character(mob, occupant):
            target = occupant
            crime = "KILLER"
            break
        if _has_player_flag(occupant, PlayerFlag.THIEF) and can_see_character(mob, occupant):
            target = occupant
            crime = "THIEF"
            break

    if target is None:
        return False

    _clear_comm_flag(mob, CommFlag.NOSHOUT)
    declaration = (
        f"{getattr(target, 'name', 'Someone')} is a {crime}!  PROTECT THE INNOCENT!  MORE BLOOOOD!!!"
    )
    _append_message(mob, f"You yell '{declaration}'")
    room.broadcast(f"{_display_name(mob)} yells '{declaration}'", exclude=mob)
    _attack(mob, target)
    return True


def spec_guard(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob) or getattr(mob, "fighting", None) is not None:
        return False

    target = None
    crime = ""
    max_evil = 300
    fallback = None

    for occupant in _room_occupants(room):
        if getattr(occupant, "is_npc", False):
            # Track evil fighters for fallback targeting
            opponent = getattr(occupant, "fighting", None)
            if opponent is not None and opponent is not mob:
                try:
                    alignment = int(getattr(occupant, "alignment", 0) or 0)
                except Exception:
                    alignment = 0
                if alignment < max_evil:
                    max_evil = alignment
                    fallback = occupant
            continue

        if _has_player_flag(occupant, PlayerFlag.KILLER) and can_see_character(mob, occupant):
            target = occupant
            crime = "KILLER"
            break
        if _has_player_flag(occupant, PlayerFlag.THIEF) and can_see_character(mob, occupant):
            target = occupant
            crime = "THIEF"
            break

        opponent = getattr(occupant, "fighting", None)
        if opponent is not None and opponent is not mob:
            try:
                alignment = int(getattr(occupant, "alignment", 0) or 0)
            except Exception:
                alignment = 0
            if alignment < max_evil:
                max_evil = alignment
                fallback = occupant

    if target is not None:
        _clear_comm_flag(mob, CommFlag.NOSHOUT)
        message = (
            f"{getattr(target, 'name', 'Someone')} is a {crime}!  PROTECT THE INNOCENT!!  BANZAI!!"
        )
        _append_message(mob, f"You yell '{message}'")
        room.broadcast(f"{_display_name(mob)} yells '{message}'", exclude=mob)
        _attack(mob, target)
        return True

    if fallback is not None:
        rally = "PROTECT THE INNOCENT!!  BANZAI!!"
        room.broadcast(f"{_display_name(mob)} screams '{rally}'", exclude=None)
        _attack(mob, fallback)
        return True

    return False


_TROLL_MEMBER_TAUNTS = [
    "$n yells 'I've been looking for you, punk!'",
    "With a scream of rage, $n attacks $N.",
    "$n says 'What's slimy Ogre trash like you doing around here?'",
    "$n cracks his knuckles and says 'Do ya feel lucky?'",
    "$n says 'There's no cops to save you this time!'",
    "$n says 'Time to join your brother, spud.'",
    "$n says 'Let's rock.'",
]


_OGRE_MEMBER_TAUNTS = [
    "$n yells 'I've been looking for you, punk!'",
    "With a scream of rage, $n attacks $N.'",
    "$n says 'What's Troll filth like you doing around here?'",
    "$n cracks his knuckles and says 'Do ya feel lucky?'",
    "$n says 'There's no cops to save you this time!'",
    "$n says 'Time to join your brother, spud.'",
    "$n says 'Let's rock.'",
]


def spec_troll_member(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if (
        room is None
        or not _is_awake(mob)
        or _has_affect(mob, AffectFlag.CALM)
        or _has_affect(mob, AffectFlag.CHARM)
        or getattr(mob, "fighting", None) is not None
    ):
        return False

    mob_level = int(getattr(mob, "level", 0) or 0)
    victim = None
    count = 0
    for candidate in _room_occupants(room):
        if candidate is mob or not getattr(candidate, "is_npc", False):
            continue
        if _prototype_vnum(candidate) == MOB_VNUM_PATROLMAN:
            return False
        if _prototype_group(candidate) != GROUP_VNUM_OGRES:
            continue
        target_level = int(getattr(candidate, "level", 0) or 0)
        if mob_level <= target_level - 2:
            continue
        if rng_mm.number_range(0, count) == 0:
            victim = candidate
        count += 1

    if victim is None:
        return False

    taunt_index = rng_mm.number_range(0, len(_TROLL_MEMBER_TAUNTS) - 1)
    _broadcast_room_message(room, _TROLL_MEMBER_TAUNTS[taunt_index], mob, victim)
    _attack(mob, victim)
    return True


def spec_ogre_member(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if (
        room is None
        or not _is_awake(mob)
        or _has_affect(mob, AffectFlag.CALM)
        or _has_affect(mob, AffectFlag.CHARM)
        or getattr(mob, "fighting", None) is not None
    ):
        return False

    mob_level = int(getattr(mob, "level", 0) or 0)
    victim = None
    count = 0
    for candidate in _room_occupants(room):
        if candidate is mob or not getattr(candidate, "is_npc", False):
            continue
        if _prototype_vnum(candidate) == MOB_VNUM_PATROLMAN:
            return False
        if _prototype_group(candidate) != GROUP_VNUM_TROLLS:
            continue
        target_level = int(getattr(candidate, "level", 0) or 0)
        if mob_level <= target_level - 2:
            continue
        if rng_mm.number_range(0, count) == 0:
            victim = candidate
        count += 1

    if victim is None:
        return False

    taunt_index = rng_mm.number_range(0, len(_OGRE_MEMBER_TAUNTS) - 1)
    _broadcast_room_message(room, _OGRE_MEMBER_TAUNTS[taunt_index], mob, victim)
    _attack(mob, victim)
    return True


def spec_patrolman(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if (
        room is None
        or not _is_awake(mob)
        or getattr(mob, "fighting", None) is not None
        or _has_affect(mob, AffectFlag.CALM)
        or _has_affect(mob, AffectFlag.CHARM)
    ):
        return False

    victim = None
    count = 0
    for occupant in _room_occupants(room):
        if occupant is mob:
            continue
        opponent = getattr(occupant, "fighting", None)
        if opponent is None:
            continue
        # Prefer higher level combatant like ROM
        candidate = occupant
        try:
            if int(getattr(opponent, "level", 0) or 0) > int(getattr(occupant, "level", 0) or 0):
                candidate = opponent
        except Exception:
            pass
        if rng_mm.number_range(0, count if count > 0 else 0) == 0:
            victim = candidate
        count += 1

    if victim is None:
        return False

    victim_spec = _spec_name(victim)
    mob_spec = _spec_name(mob)
    if victim_spec is not None and victim_spec == mob_spec and getattr(victim, "is_npc", False):
        return False

    whistle = _find_whistle(mob)
    if whistle is not None:
        descriptor = getattr(whistle, "short_descr", None) or getattr(whistle, "name", "whistle")
        _append_message(mob, f"You blow down hard on {descriptor}.")
        room.broadcast(
            f"{_display_name(mob)} blows on {descriptor}, ***WHEEEEEEEEEEEET***",
            exclude=mob,
        )
        _broadcast_area(room, "You hear a shrill whistling sound.")

    message_map = {
        0: "yells 'All roit! All roit! break it up!'",
        1: "says 'Society's to blame, but what's a bloke to do?'",
        2: "mumbles 'bloody kids will be the death of us all.'",
        3: "shouts 'Stop that! Stop that!' and attacks.",
        4: "pulls out his billy and goes to work.",
        5: "sighs in resignation and proceeds to break up the fight.",
        6: "says 'Settle down, you hooligans!'",
    }
    roll = rng_mm.number_range(0, 6)
    speech = message_map.get(roll)
    if speech is not None:
        room.broadcast(f"{_display_name(mob)} {speech}", exclude=None)

    _attack(mob, victim)
    return True


# --- Caster special functions ---


def spec_cast_cleric(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "blindness"),
        1: (3, "cause serious"),
        2: (7, "earthquake"),
        3: (9, "cause critical"),
        4: (10, "dispel evil"),
        5: (12, "curse"),
        6: (12, "change sex"),
        7: (13, "flamestrike"),
        8: (15, "harm"),
        9: (15, "harm"),
        10: (15, "harm"),
        11: (15, "plague"),
    }
    default = (16, "dispel magic")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_mage(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "blindness"),
        1: (3, "chill touch"),
        2: (7, "weaken"),
        3: (8, "teleport"),
        4: (11, "colour spray"),
        5: (12, "change sex"),
        6: (13, "energy drain"),
        7: (15, "fireball"),
        8: (15, "fireball"),
        9: (15, "fireball"),
        10: (20, "plague"),
    }
    default = (20, "acid blast")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_undead(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "curse"),
        1: (3, "weaken"),
        2: (6, "chill touch"),
        3: (9, "blindness"),
        4: (12, "poison"),
        5: (15, "energy drain"),
        6: (18, "harm"),
        7: (21, "teleport"),
        8: (20, "plague"),
    }
    default = (18, "harm")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_judge(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False
    return _cast_spell(mob, victim, "high explosive")


register_spec_fun("spec_mayor", spec_mayor)
register_spec_fun("spec_janitor", spec_janitor)
register_spec_fun("spec_fido", spec_fido)
register_spec_fun("spec_poison", spec_poison)
register_spec_fun("spec_executioner", spec_executioner)
register_spec_fun("spec_guard", spec_guard)
register_spec_fun("spec_patrolman", spec_patrolman)
register_spec_fun("spec_troll_member", spec_troll_member)
register_spec_fun("spec_ogre_member", spec_ogre_member)
register_spec_fun("spec_nasty", spec_nasty)
register_spec_fun("spec_thief", spec_thief)
register_spec_fun("spec_cast_cleric", spec_cast_cleric)
register_spec_fun("spec_cast_mage", spec_cast_mage)
register_spec_fun("spec_cast_undead", spec_cast_undead)
register_spec_fun("spec_cast_judge", spec_cast_judge)
