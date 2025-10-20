from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mud.characters import is_same_group
from mud.skills.registry import skill_registry
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


def _parse_numbered_token(token: str) -> tuple[int, str]:
    text = (token or "").strip()
    if not text:
        return 1, ""
    if "." not in text:
        return 1, text
    prefix, remainder = text.split(".", 1)
    try:
        index = int(prefix or "0")
    except ValueError:
        index = 0
    return index, remainder.strip()


def _is_name_match(search: str, candidate: str | None) -> bool:
    if not search or candidate is None:
        return False
    search_text = search.strip().lower()
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
    return all(any(word.startswith(part) for word in candidate_words) for part in parts)


def _iter_char_candidates(char: Character) -> Iterable[str]:
    for attr in ("name", "short_descr", "long_descr"):
        value = getattr(char, attr, None)
        if isinstance(value, str) and value.strip():
            yield value
    proto = getattr(char, "prototype", None)
    if proto is not None:
        for attr in ("player_name", "short_descr", "long_descr"):
            value = getattr(proto, attr, None)
            if isinstance(value, str) and value.strip():
                yield value


def _match_char_name(char: Character, token: str) -> bool:
    if not token:
        return False
    return any(_is_name_match(token, candidate) for candidate in _iter_char_candidates(char))


def _find_char_in_room(ch: Character, name: str) -> Character | None:
    room = getattr(ch, "room", None)
    index, token = _parse_numbered_token(name)
    if index <= 0:
        index = 1
    search = token or name.strip()
    if not search:
        return None
    for occupant in _iter_room_people(room):
        if _match_char_name(occupant, search):
            index -= 1
            if index <= 0:
                return occupant
    return None


def _find_char_world(name: str) -> Character | None:
    index, token = _parse_numbered_token(name)
    if index <= 0:
        index = 1
    search = token or name.strip()
    if not search:
        return None
    from mud.models.character import character_registry

    for candidate in list(character_registry):
        if _match_char_name(candidate, search):
            index -= 1
            if index <= 0:
                return candidate
    return None


def _iter_obj_candidates(obj: Object | None) -> Iterable[str]:
    if obj is None:
        return []
    candidates: list[str] = []
    for attr in ("name", "short_descr"):
        value = getattr(obj, attr, None)
        if isinstance(value, str) and value.strip():
            candidates.append(value)
    prototype = getattr(obj, "prototype", None)
    if prototype is not None:
        for attr in ("name", "short_descr"):
            value = getattr(prototype, attr, None)
            if isinstance(value, str) and value.strip():
                candidates.append(value)
    return candidates


def _match_obj_name(obj: Object | None, token: str) -> bool:
    if not token:
        return False
    return any(_is_name_match(token, candidate) for candidate in _iter_obj_candidates(obj))


def _find_obj_here(ch: Character, token: str) -> Object | None:
    if not token:
        return None
    index, search_token = _parse_numbered_token(token)
    if index <= 0:
        index = 1
    search = search_token or token.strip()
    if not search:
        return None
    room = getattr(ch, "room", None)
    if room is not None:
        for obj in list(getattr(room, "contents", []) or []):
            if _match_obj_name(obj, search):
                index -= 1
                if index <= 0:
                    return obj
    for obj in list(getattr(ch, "inventory", []) or []):
        if _match_obj_name(obj, search):
            index -= 1
            if index <= 0:
                return obj
    equipment = getattr(ch, "equipment", {}) or {}
    for obj in equipment.values():
        if _match_obj_name(obj, search):
            index -= 1
            if index <= 0:
                return obj
    return None


def _extract_character(victim: Character) -> None:
    """Remove a character from the world, mirroring ROM extract_char."""

    from mud.models.character import character_registry

    room = getattr(victim, "room", None)
    if room is not None:
        remover = getattr(room, "remove_character", None)
        if callable(remover):
            remover(victim)
        else:
            people = getattr(room, "people", None)
            if people and victim in people:
                people.remove(victim)
            area = getattr(room, "area", None)
            if area is not None and not getattr(victim, "is_npc", True):
                current = int(getattr(area, "nplayer", 0))
                area.nplayer = max(0, current - 1)
            if getattr(victim, "room", None) is room:
                victim.room = None
    try:
        character_registry.remove(victim)
    except ValueError:
        pass


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


def do_mpat(ch: Character, argument: str) -> None:
    location_token, _, command = argument.partition(" ")
    if not location_token or not command.strip():
        return
    destination = _find_location(ch, location_token)
    if destination is None:
        return
    original_room = getattr(ch, "room", None)
    original_on = getattr(ch, "on", None)
    if destination is original_room:
        from mud.commands.dispatcher import process_command

        process_command(ch, command.strip())
        return
    _move_to_room(ch, destination)
    from mud.commands.dispatcher import process_command
    process_command(ch, command.strip())
    from mud.models.character import character_registry

    if ch in character_registry:
        if original_room is not None:
            _move_to_room(ch, original_room)
        ch.on = original_on


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


def _split_spell_argument(argument: str) -> tuple[str, str]:
    raw = argument.strip()
    if not raw:
        return "", ""
    if raw[0] in {"'", '"'}:
        terminator = raw[0]
        end_index = raw.find(terminator, 1)
        if end_index == -1:
            spell = raw[1:].strip()
            return spell, ""
        spell = raw[1:end_index].strip()
        rest = raw[end_index + 1 :].strip()
        return spell, rest
    spell, _, rest = raw.partition(" ")
    return spell, rest.strip()


def do_mpcast(ch: Character, argument: str) -> None:
    spell_name, rest = _split_spell_argument(argument)
    if not spell_name:
        return
    spell = skill_registry.find_spell(ch, spell_name)
    if spell is None:
        return
    handler = skill_registry.handlers.get(spell.name)
    if handler is None:
        return

    target_token = rest.strip()
    target_kind = (getattr(spell, "target", "victim") or "victim").lower()

    if target_kind == "ignore":
        target: Character | Object | None = None
    elif target_kind == "victim":
        victim = _find_char_in_room(ch, target_token)
        if victim is None or victim is ch:
            return
        target = victim
    elif target_kind == "friendly":
        if target_token:
            victim = _find_char_in_room(ch, target_token)
            if victim is None:
                return
            target = victim
        else:
            target = ch
    elif target_kind == "self":
        target = ch
    elif target_kind == "object":
        obj = _find_obj_here(ch, target_token)
        if obj is None:
            return
        target = obj
    elif target_kind == "character_or_object":
        if not target_token:
            return
        victim = _find_char_in_room(ch, target_token)
        if victim is not None:
            target = victim
        else:
            obj = _find_obj_here(ch, target_token)
            if obj is None:
                return
            target = obj
    else:
        return

    handler(ch, target)


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


def _find_object_for_transfer(
    ch: Character, token: str
) -> tuple[Object | None, str | tuple[str, str] | None]:
    room = getattr(ch, "room", None)
    for obj in list(getattr(room, "contents", []) or []):
        if _match_object(obj, token):
            return obj, "room"
    for obj in list(getattr(ch, "inventory", []) or []):
        if _match_object(obj, token):
            return obj, "inventory"
    equipment = getattr(ch, "equipment", None)
    if isinstance(equipment, dict):
        for slot, equipped in equipment.items():
            if equipped is not None and _match_object(equipped, token):
                return equipped, ("equipment", str(slot))
    return None, None


def _remove_object_from_source(
    ch: Character, obj: Object, source: str | tuple[str, str] | None
) -> None:
    if source == "room":
        room = getattr(ch, "room", None)
        contents = getattr(room, "contents", None)
        if contents and obj in contents:
            contents.remove(obj)
        if getattr(obj, "location", None) is room:
            obj.location = None
        return
    remover = getattr(ch, "remove_object", None)
    if callable(remover):
        remover(obj)
        return
    if source == "inventory":
        inventory = getattr(ch, "inventory", None)
        if inventory and obj in inventory:
            inventory.remove(obj)
        return
    if isinstance(source, tuple) and source and source[0] == "equipment":
        equipment = getattr(ch, "equipment", None)
        if isinstance(equipment, dict):
            slot_key = source[1]
            if equipment.get(slot_key) is obj:
                equipment.pop(slot_key, None)


def do_mpotransfer(ch: Character, argument: str) -> None:
    token, _, rest = argument.partition(" ")
    obj_token = token.strip()
    location_token = rest.strip()
    if not obj_token or not location_token:
        return
    destination = _resolve_transfer_location(ch, location_token)
    if destination is None:
        return
    obj, source = _find_object_for_transfer(ch, obj_token)
    if obj is None:
        return
    _remove_object_from_source(ch, obj, source)
    adder = getattr(destination, "add_object", None)
    if callable(adder):
        adder(obj)
    else:
        contents = getattr(destination, "contents", None)
        if contents is None:
            contents = []
            destination.contents = contents  # type: ignore[attr-defined]
        if obj not in contents:
            contents.append(obj)
        if hasattr(obj, "location"):
            obj.location = destination


def do_mpgoto(ch: Character, argument: str) -> None:
    destination = _find_location(ch, argument.strip())
    if destination is None:
        return
    if getattr(ch, "fighting", None) is not None:
        ch.fighting = None
    _move_to_room(ch, destination)


def _purge_object(ch: Character, obj: Object) -> None:
    room = getattr(ch, "room", None)
    if room is not None:
        contents = getattr(room, "contents", None)
        if contents and obj in contents:
            contents.remove(obj)
        if getattr(obj, "location", None) is room:
            obj.location = None
    inventory = getattr(ch, "inventory", None)
    if inventory and obj in inventory:
        inventory.remove(obj)
    equipment = getattr(ch, "equipment", None)
    if isinstance(equipment, dict):
        for slot, equipped in list(equipment.items()):
            if equipped is obj:
                equipment.pop(slot, None)


def do_mppurge(ch: Character, argument: str) -> None:
    token = argument.strip()
    room = getattr(ch, "room", None)
    if room is None:
        return

    if not token or token.lower() == "all":
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is ch:
                continue
            if not getattr(occupant, "is_npc", False):
                continue
            _extract_character(occupant)
        for obj in list(getattr(room, "contents", []) or []):
            _purge_object(ch, obj)
        return

    victim = _find_char_in_room(ch, token)
    if victim is not None:
        if not getattr(victim, "is_npc", False):
            return
        _extract_character(victim)
        return

    target_obj: Object | None = None
    for obj in list(getattr(room, "contents", []) or []):
        if _match_object(obj, token):
            target_obj = obj
            break
    if target_obj is None:
        for obj in list(getattr(ch, "inventory", []) or []):
            if _match_object(obj, token):
                target_obj = obj
                break
    if target_obj is None:
        for equipped in list(getattr(ch, "equipment", {}).values()):
            if equipped is not None and _match_object(equipped, token):
                target_obj = equipped
                break
    if target_obj is None:
        return
    _purge_object(ch, target_obj)


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


def do_mpgtransfer(ch: Character, argument: str) -> None:
    leader_token, _, rest = argument.partition(" ")
    leader_name = leader_token.strip()
    destination_token = rest.strip()
    if not leader_name:
        return
    leader = _find_char_in_room(ch, leader_name)
    if leader is None:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    for occupant in list(_iter_room_people(room)):
        if not is_same_group(leader, occupant):
            continue
        target_name = getattr(occupant, "name", "") or ""
        if not target_name:
            continue
        command = target_name if not destination_token else f"{target_name} {destination_token}"
        do_mptransfer(ch, command)


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


def do_mpgforce(ch: Character, argument: str) -> None:
    target_name, _, command = argument.partition(" ")
    command = command.strip()
    if not target_name or not command:
        return
    victim = _find_char_in_room(ch, target_name)
    if victim is None or victim is ch:
        return
    from mud.commands.dispatcher import process_command

    room = getattr(victim, "room", None)
    for occupant in _iter_room_people(room):
        if not is_same_group(victim, occupant):
            continue
        if occupant is ch:
            continue
        process_command(occupant, command)


def do_mpvforce(ch: Character, argument: str) -> None:
    vnum_token, _, command = argument.partition(" ")
    command = command.strip()
    if not vnum_token or not command:
        return
    try:
        target_vnum = int(vnum_token)
    except ValueError:
        return
    from mud.commands.dispatcher import process_command
    from mud.models.character import character_registry

    for candidate in list(character_registry):
        if candidate is ch:
            continue
        if not getattr(candidate, "is_npc", False):
            continue
        prototype = getattr(candidate, "prototype", None)
        proto_vnum = getattr(prototype, "vnum", None)
        if proto_vnum != target_vnum:
            continue
        if getattr(candidate, "fighting", None) is not None:
            continue
        process_command(candidate, command)


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
    return _match_obj_name(obj, token)


def do_mpjunk(ch: Character, argument: str) -> None:
    token = argument.strip()
    if not token:
        return

    def _is_carried(obj: Object) -> bool:
        inventory = getattr(ch, "inventory", []) or []
        if obj in inventory:
            return True
        equipment = getattr(ch, "equipment", {}) or {}
        return any(equipped is obj for equipped in equipment.values())

    def _strip_from_collections(obj: Object) -> None:
        removed = False
        inventory = getattr(ch, "inventory", None)
        if isinstance(inventory, list):
            while obj in inventory:
                inventory.remove(obj)
                removed = True
        equipment = getattr(ch, "equipment", None)
        if isinstance(equipment, dict):
            for slot, equipped in list(equipment.items()):
                if equipped is obj:
                    del equipment[slot]
                    removed = True
        if removed and hasattr(ch, "carry_number"):
            try:
                ch.carry_number = max(0, int(getattr(ch, "carry_number", 0)) - 1)
            except Exception:
                pass
        recalc = getattr(ch, "_recalculate_carry_weight", None)
        if callable(recalc):
            recalc()

    def _extract_runtime_object(obj: Object) -> None:
        if any(hasattr(obj, attr) for attr in ("contains", "carried_by", "in_room", "in_obj")):
            try:
                from mud.game_loop import _extract_obj as _legacy_extract_obj
            except ImportError:  # pragma: no cover - defensive
                _legacy_extract_obj = None
            if _legacy_extract_obj is not None:
                _legacy_extract_obj(obj)  # type: ignore[arg-type]
            return

        for attr in ("contained_items", "contains"):
            contents = list(getattr(obj, attr, []) or [])
            for item in contents:
                _extract_runtime_object(item)
            collection = getattr(obj, attr, None)
            if isinstance(collection, list):
                collection.clear()

        container = getattr(obj, "location", None)
        if container is not None:
            contents = getattr(container, "contents", None)
            if isinstance(contents, list):
                while obj in contents:
                    contents.remove(obj)
        if hasattr(obj, "location"):
            obj.location = None

    def _discard(obj: Object) -> None:
        if obj is None:
            return
        was_carried = _is_carried(obj)
        remover = getattr(ch, "remove_object", None)
        if callable(remover):
            try:
                remover(obj)  # type: ignore[arg-type]
            except Exception:
                pass
        if was_carried and _is_carried(obj):
            _strip_from_collections(obj)

        if hasattr(obj, "carried_by"):
            setattr(obj, "carried_by", None)
        _extract_runtime_object(obj)

    def _iter_carried_objects() -> list[Object]:
        seen: set[int] = set()
        collected: list[Object] = []
        for obj in list(getattr(ch, "inventory", []) or []):
            key = id(obj)
            if key in seen:
                continue
            seen.add(key)
            collected.append(obj)
        equipment = getattr(ch, "equipment", {}) or {}
        for obj in equipment.values():
            key = id(obj)
            if key in seen:
                continue
            seen.add(key)
            collected.append(obj)
        return collected

    lower = token.lower()
    if lower == "all":
        for obj in _iter_carried_objects():
            _discard(obj)
        return
    if lower.startswith("all."):
        suffix = token[4:]
        for obj in _iter_carried_objects():
            if not suffix or _match_object(obj, suffix):
                _discard(obj)
        return

    number, remainder = _parse_numbered_token(token)
    if number <= 0:
        number = 1
    search = remainder or token
    equipment = getattr(ch, "equipment", {}) or {}
    remaining = number
    for obj in equipment.values():
        if _match_object(obj, search):
            remaining -= 1
            if remaining <= 0:
                _discard(obj)
                return
    remaining = number
    for obj in list(getattr(ch, "inventory", []) or []):
        if _match_object(obj, search):
            remaining -= 1
            if remaining <= 0:
                _discard(obj)
                return


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


def do_mpremember(ch: Character, argument: str) -> None:
    target_name = argument.strip()
    if not target_name:
        return
    target = _find_char_world(target_name)
    if target is None:
        return
    ch.mprog_target = target


def do_mpforget(ch: Character, argument: str) -> None:
    ch.mprog_target = None


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
    MobCommand("at", do_mpat),
    MobCommand("purge", do_mppurge),
    MobCommand("transfer", do_mptransfer),
    MobCommand("gtransfer", do_mpgtransfer),
    MobCommand("otransfer", do_mpotransfer),
    MobCommand("cast", do_mpcast),
    MobCommand("gforce", do_mpgforce),
    MobCommand("vforce", do_mpvforce),
    MobCommand("force", do_mpforce),
    MobCommand("kill", do_mpkill),
    MobCommand("assist", do_mpassist),
    MobCommand("junk", do_mpjunk),
    MobCommand("damage", do_mpdamage),
    MobCommand("remember", do_mpremember),
    MobCommand("forget", do_mpforget),
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
