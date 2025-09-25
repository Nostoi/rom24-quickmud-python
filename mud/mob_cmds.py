from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mud.utils import rng_mm

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object
    from mud.models.room import Room


CommandFunc = Callable[["Character", str], None]


@dataclass(frozen=True)
class MobCommand:
    name: str
    func: CommandFunc


def _split_command(argument: str) -> tuple[str, str]:
    stripped = argument.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(None, 1)
    command = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    return command, rest


def _iter_room_people(room: Room | None) -> Iterable[Character]:
    if room is None:
        return []
    return list(getattr(room, "people", []) or [])


def _match_char_name(char: Character, token: str) -> bool:
    name = getattr(char, "name", None)
    if not name or not token:
        return False
    return name.lower().startswith(token.lower())


def _find_char_in_room(ch: Character, name: str) -> Character | None:
    room = getattr(ch, "room", None)
    for occupant in _iter_room_people(room):
        if _match_char_name(occupant, name):
            return occupant
    return None


def _find_char_world(name: str) -> Character | None:
    if not name:
        return None
    from mud.models.character import character_registry

    for candidate in list(character_registry):
        if _match_char_name(candidate, name):
            return candidate
    return None


def _get_room_by_vnum(vnum: int) -> Room | None:
    from mud.registry import room_registry

    return room_registry.get(vnum)


def _find_location(ch: Character, token: str) -> Room | None:
    if not token:
        return None
    if token.lower() == "here":
        return getattr(ch, "room", None)
    try:
        vnum = int(token)
    except ValueError:
        target = _find_char_world(token)
        return getattr(target, "room", None)
    return _get_room_by_vnum(vnum)


def _move_to_room(ch: Character, destination: Room) -> None:
    current = getattr(ch, "room", None)
    if current is destination:
        return
    if current is not None:
        remover = getattr(current, "remove_character", None)
        if callable(remover):
            remover(ch)
    adder = getattr(destination, "add_character", None)
    if callable(adder):
        adder(ch)
    else:
        destination.people.append(ch)
        ch.room = destination


def _append_message(target: Character, message: str) -> None:
    if not hasattr(target, "messages"):
        return
    target.messages.append(message)


def _broadcast(
    room: Room | None,
    message: str,
    *,
    exclude: Iterable[object] | None = None,
) -> None:
    if not room or not message:
        return
    excluded = tuple(exclude or ())
    for char in _iter_room_people(room):
        if any(char is other for other in excluded):
            continue
        _append_message(char, message)


def do_mpecho(ch: Character, argument: str) -> None:
    if not argument:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    room.broadcast(argument, exclude=ch)


def do_mpasound(ch: Character, argument: str) -> None:
    if not argument:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    exits = list(getattr(room, "exits", []) or [])
    for exit_obj in exits:
        if exit_obj is None:
            continue
        target_room = getattr(exit_obj, "to_room", None)
        if target_room is None or target_room is room:
            continue
        _broadcast(target_room, argument)


def do_mpgecho(ch: Character, argument: str) -> None:
    if not argument:
        return
    from mud.models.character import character_registry

    for target in character_registry:
        if hasattr(target, "messages"):
            target.messages.append(argument)


def do_mpzecho(ch: Character, argument: str) -> None:
    if not argument:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    area = getattr(room, "area", None)
    if area is None:
        return
    from mud.models.character import character_registry

    for target in list(character_registry):
        target_room = getattr(target, "room", None)
        if target_room is None:
            continue
        if getattr(target_room, "area", None) is not area:
            continue
        _append_message(target, argument)


def do_mpechoaround(ch: Character, argument: str) -> None:
    target_name, _, message = argument.partition(" ")
    if not target_name or not message.strip():
        return
    victim = _find_char_in_room(ch, target_name)
    if victim is None:
        return
    room = getattr(ch, "room", None)
    for occupant in _iter_room_people(room):
        if occupant is ch or occupant is victim:
            continue
        _append_message(occupant, message.strip())


def do_mpechoat(ch: Character, argument: str) -> None:
    target_name, _, message = argument.partition(" ")
    if not target_name or not message.strip():
        return
    victim = _find_char_in_room(ch, target_name)
    if victim is None:
        return
    _append_message(victim, message.strip())


def do_mpcall(ch: Character, argument: str) -> None:
    args = argument.split()
    if not args:
        return
    try:
        vnum = int(args[0])
    except ValueError:
        return
    target = None
    if len(args) > 1:
        target = _find_char_in_room(ch, args[1])
    from mud import mobprog

    context = getattr(ch, "_mp_context", None)
    mobprog.call_prog(vnum, ch, target, context=context)


def do_mpdelay(ch: Character, argument: str) -> None:
    parts = argument.split()
    delay = 0
    if parts:
        try:
            delay = int(parts[0])
        except ValueError:
            delay = 0
    ch.mprog_delay = max(0, delay)


def do_mpcancel(ch: Character, argument: str) -> None:
    ch.mprog_delay = 0


def do_mpmload(ch: Character, argument: str) -> None:
    parts = argument.split()
    if not parts:
        return
    try:
        vnum = int(parts[0])
    except ValueError:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    from mud.spawning.mob_spawner import spawn_mob

    mob = spawn_mob(vnum)
    if mob is None:
        return
    mob.is_npc = True
    proto = getattr(mob, "prototype", None)
    default_pos = getattr(proto, "default_pos", getattr(mob, "position", None))
    if default_pos is not None:
        mob.default_pos = default_pos
    if not hasattr(mob, "messages"):
        mob.messages = []
    programs = getattr(getattr(mob, "prototype", None), "mprogs", None)
    if programs is not None and not getattr(mob, "mob_programs", None):
        mob.mob_programs = list(programs)
    room.add_mob(mob)


def do_mpoload(ch: Character, argument: str) -> None:
    parts = argument.split()
    if not parts:
        return
    try:
        vnum = int(parts[0])
    except ValueError:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    mode_token = ""
    if len(parts) >= 2:
        if parts[1].isdigit():
            if len(parts) >= 3:
                mode_token = parts[2]
        else:
            mode_token = parts[1]
    mode = mode_token.lower()
    from mud.spawning.obj_spawner import spawn_object

    obj = spawn_object(vnum)
    if obj is None:
        return
    if mode.startswith("r"):
        room.add_object(obj)
        return
    inventory = getattr(ch, "inventory", None)
    if inventory is None:
        inventory = []
        ch.inventory = inventory
    inventory.append(obj)


def _resolve_transfer_location(ch: Character, token: str) -> Room | None:
    if not token:
        return getattr(ch, "room", None)
    return _find_location(ch, token)


def _transfer_character(ch: Character, victim: Character, dest: Room) -> None:
    if getattr(victim, "room", None) is dest:
        return
    if getattr(victim, "fighting", None) is not None:
        victim.fighting = None
    current = getattr(victim, "room", None)
    if current is not None:
        remover = getattr(current, "remove_character", None)
        if callable(remover):
            remover(victim)
    adder = getattr(dest, "add_character", None)
    if callable(adder):
        adder(victim)
    else:
        dest.people.append(victim)
        victim.room = dest


def do_mpgoto(ch: Character, argument: str) -> None:
    destination = _find_location(ch, argument.strip())
    if destination is None:
        return
    if getattr(ch, "fighting", None) is not None:
        ch.fighting = None
    _move_to_room(ch, destination)


def do_mptransfer(ch: Character, argument: str) -> None:
    first, _, rest = argument.partition(" ")
    target_name = first.strip()
    location_token = rest.strip()
    if not target_name:
        return
    destination = _resolve_transfer_location(ch, location_token)
    if destination is None:
        return
    if target_name.lower() == "all":
        for occupant in list(_iter_room_people(getattr(ch, "room", None))):
            if getattr(occupant, "is_npc", True):
                continue
            _transfer_character(ch, occupant, destination)
        return
    victim = _find_char_world(target_name)
    if victim is None:
        return
    _transfer_character(ch, victim, destination)


def do_mpforce(ch: Character, argument: str) -> None:
    target_name, _, command = argument.partition(" ")
    if not target_name or not command.strip():
        return
    from mud.commands.dispatcher import process_command

    if target_name.lower() == "all":
        for occupant in _iter_room_people(getattr(ch, "room", None)):
            if occupant is ch:
                continue
            process_command(occupant, command)
        return
    victim = _find_char_in_room(ch, target_name)
    if victim is None or victim is ch:
        return
    process_command(victim, command)


def do_mpkill(ch: Character, argument: str) -> None:
    target = _find_char_in_room(ch, argument.strip())
    if target is None:
        return
    if getattr(target, "is_npc", False):
        return
    if getattr(ch, "fighting", None) is not None:
        return
    from mud.combat import multi_hit

    multi_hit(ch, target)


def do_mpassist(ch: Character, argument: str) -> None:
    ally = _find_char_in_room(ch, argument.strip())
    if ally is None:
        return
    target = getattr(ally, "fighting", None)
    if target is None:
        return
    from mud.combat import multi_hit

    multi_hit(ch, target)


def _match_object(obj: Object, token: str) -> bool:
    proto = getattr(obj, "prototype", None)
    names: list[str] = []
    if proto is not None:
        for attr in ("name", "short_descr"):
            value = getattr(proto, attr, None)
            if value:
                names.extend(str(value).lower().split())
    if hasattr(obj, "name") and getattr(obj, "name", None):
        names.extend(str(obj.name).lower().split())
    token = token.lower()
    return any(name.startswith(token) or token in name for name in names)


def do_mpjunk(ch: Character, argument: str) -> None:
    token = argument.strip()
    if not token:
        return
    inventory = list(getattr(ch, "inventory", []) or [])
    equipment = dict(getattr(ch, "equipment", {}) or {})

    def _remove(obj: Object) -> None:
        if obj in inventory:
            inventory.remove(obj)
        for slot, equipped in list(equipment.items()):
            if equipped is obj:
                equipment.pop(slot, None)

    if token.lower() == "all":
        for obj in list(inventory):
            _remove(obj)
        ch.inventory = []
        ch.equipment = equipment
        return
    if token.lower().startswith("all."):
        suffix = token[4:]
        for obj in list(inventory):
            if _match_object(obj, suffix):
                _remove(obj)
        ch.inventory = inventory
        ch.equipment = equipment
        return
    for obj in list(inventory):
        if _match_object(obj, token):
            _remove(obj)
            break
    ch.inventory = inventory
    ch.equipment = equipment


def do_mpdamage(ch: Character, argument: str) -> None:
    parts = argument.split()
    if len(parts) < 3:
        return
    target_token, min_raw, max_raw, *rest = parts
    try:
        low = int(min_raw)
        high = int(max_raw)
    except ValueError:
        return
    if low > high:
        low, high = high, low
    kill = bool(rest)

    def _apply_damage(victim: Character) -> None:
        amount = rng_mm.number_range(low, high)
        if not kill:
            amount = min(amount, max(0, getattr(victim, "hit", 0)))
        victim.hit = max(0, getattr(victim, "hit", 0) - amount)

    if target_token.lower() == "all":
        for occupant in _iter_room_people(getattr(ch, "room", None)):
            if occupant is ch:
                continue
            _apply_damage(occupant)
        return
    victim = _find_char_in_room(ch, target_token)
    if victim is None:
        return
    _apply_damage(victim)


def do_mpremove(ch: Character, argument: str) -> None:
    target_name, _, obj_token = argument.partition(" ")
    if not target_name or not obj_token.strip():
        return
    victim = _find_char_in_room(ch, target_name)
    if victim is None:
        return
    inventory = list(getattr(victim, "inventory", []) or [])
    all_flag = obj_token.strip().lower() == "all"
    vnum = None
    if not all_flag:
        try:
            vnum = int(obj_token.strip())
        except ValueError:
            return
    new_inventory: list[Object] = []
    for obj in inventory:
        proto = getattr(obj, "prototype", None)
        proto_vnum = getattr(proto, "vnum", None)
        if all_flag or (proto_vnum is not None and proto_vnum == vnum):
            continue
        new_inventory.append(obj)
    victim.inventory = new_inventory


def do_mpflee(ch: Character, argument: str) -> None:
    if getattr(ch, "fighting", None) is not None:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    from mud.models.constants import EX_CLOSED

    exits = list(getattr(room, "exits", []) or [])
    for exit_obj in exits:
        if exit_obj is None:
            continue
        if getattr(exit_obj, "exit_info", 0) & EX_CLOSED:
            continue
        target_room = getattr(exit_obj, "to_room", None)
        if target_room is None:
            continue
        _move_to_room(ch, target_room)
        return


_COMMANDS: list[MobCommand] = [
    MobCommand("asound", do_mpasound),
    MobCommand("echo", do_mpecho),
    MobCommand("gecho", do_mpgecho),
    MobCommand("zecho", do_mpzecho),
    MobCommand("echoaround", do_mpechoaround),
    MobCommand("echoat", do_mpechoat),
    MobCommand("mload", do_mpmload),
    MobCommand("oload", do_mpoload),
    MobCommand("goto", do_mpgoto),
    MobCommand("transfer", do_mptransfer),
    MobCommand("force", do_mpforce),
    MobCommand("kill", do_mpkill),
    MobCommand("assist", do_mpassist),
    MobCommand("junk", do_mpjunk),
    MobCommand("damage", do_mpdamage),
    MobCommand("remove", do_mpremove),
    MobCommand("flee", do_mpflee),
    MobCommand("call", do_mpcall),
    MobCommand("delay", do_mpdelay),
    MobCommand("cancel", do_mpcancel),
]

_COMMAND_LOOKUP = {cmd.name: cmd for cmd in _COMMANDS}


def mob_interpret(ch: Character, argument: str) -> None:
    command_name, rest = _split_command(argument)
    if not command_name:
        return
    command = _COMMAND_LOOKUP.get(command_name)
    if command is None:
        for candidate in _COMMANDS:
            if candidate.name.startswith(command_name):
                command = candidate
                break
    if command is None:
        return
    command.func(ch, rest)
