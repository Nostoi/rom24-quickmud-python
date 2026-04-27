"""
Door commands: open, close, lock, unlock, pick.

ROM Reference: src/act_move.c
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import (
    Direction,
    ExtraFlag,
    ItemType,
    ContainerFlag,
    EX_ISDOOR,
    EX_CLOSED,
    EX_LOCKED,
    EX_PICKPROOF,
    EX_NOCLOSE,
    EX_NOLOCK,
)
from mud.world.obj_find import get_obj_here, get_obj_carry


# Direction name mapping
_DIR_NAMES = {
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

# Reverse directions for opening doors from both sides
_REV_DIR = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}


def _find_door(char: Character, arg: str) -> tuple[int | None, str]:
    """
    Find a door by direction name or keyword.

    ROM Reference: src/act_move.c find_door

    Returns: (door_index, error_message)
    """
    room = getattr(char, "room", None)
    if not room:
        return None, "You're not anywhere."

    arg = arg.lower().strip()

    # Check if it's a direction
    if arg in _DIR_NAMES:
        direction = _DIR_NAMES[arg]
        exits = getattr(room, "exits", [])

        if not exits or direction >= len(exits) or exits[direction] is None:
            return None, "I see no door in that direction."

        pexit = exits[direction]
        exit_info = getattr(pexit, "exit_info", 0)

        if not (exit_info & EX_ISDOOR):
            return None, "I see no door in that direction."

        return int(direction), ""

    # Check exit keywords
    exits = getattr(room, "exits", [])
    for i, pexit in enumerate(exits):
        if pexit is None:
            continue

        keyword = getattr(pexit, "keyword", "") or ""
        exit_info = getattr(pexit, "exit_info", 0)

        if arg in keyword.lower().split() and (exit_info & EX_ISDOOR):
            return i, ""

    return None, f"I see no {arg} here."


def do_open(char: Character, args: str) -> str:
    """
    Open a door, container, or portal.

    ROM Reference: src/act_move.c do_open (lines 345-455)

    Usage: open <door/container/direction>
    """
    args = args.strip()

    if not args:
        return "Open what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # Check for object first (container or portal)
    obj = get_obj_here(char, args)
    if obj:
        item_type = getattr(obj, "item_type", 0)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])

        # Portal
        if item_type == ItemType.PORTAL:
            if not (values[1] & EX_ISDOOR):
                return "You can't do that."
            if not (values[1] & EX_CLOSED):
                return "It's already open."
            if values[1] & EX_LOCKED:
                return "It's locked."

            obj.value[1] = values[1] & ~EX_CLOSED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You open {obj_name}."

        # Container
        if item_type == ItemType.CONTAINER:
            if not (values[1] & ContainerFlag.CLOSEABLE):
                return "You can't do that."
            if not (values[1] & ContainerFlag.CLOSED):
                return "It's already open."
            if values[1] & ContainerFlag.LOCKED:
                return "It's locked."

            obj.value[1] = values[1] & ~ContainerFlag.CLOSED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You open {obj_name}."

        return "That's not a container."

    # Check for door
    door, error = _find_door(char, args)
    if door is None:
        return error

    exits = getattr(room, "exits", [])
    pexit = exits[door]
    exit_info = getattr(pexit, "exit_info", 0)

    if not (exit_info & EX_CLOSED):
        return "It's already open."
    if exit_info & EX_LOCKED:
        return "It's locked."

    # Open this side
    pexit.exit_info = exit_info & ~EX_CLOSED

    # Open the other side
    to_room = getattr(pexit, "to_room", None)
    if to_room:
        rev_dir = _REV_DIR.get(Direction(door))
        if rev_dir is not None:
            rev_exits = getattr(to_room, "exits", [])
            if rev_exits and rev_dir < len(rev_exits) and rev_exits[rev_dir]:
                pexit_rev = rev_exits[rev_dir]
                rev_to = getattr(pexit_rev, "to_room", None)
                if rev_to is room:
                    rev_info = getattr(pexit_rev, "exit_info", 0)
                    pexit_rev.exit_info = rev_info & ~EX_CLOSED

    return "Ok."


def do_close(char: Character, args: str) -> str:
    """
    Close a door, container, or portal.

    ROM Reference: src/act_move.c do_close (lines 457-570)

    Usage: close <door/container/direction>
    """
    args = args.strip()

    if not args:
        return "Close what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # Check for object first (container or portal)
    obj = get_obj_here(char, args)
    if obj:
        item_type = getattr(obj, "item_type", 0)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])

        # Portal (ROM C lines 477-493)
        if item_type == ItemType.PORTAL:
            if not (values[1] & EX_ISDOOR) or (values[1] & EX_NOCLOSE):
                return "You can't do that."
            if values[1] & EX_CLOSED:
                return "It's already closed."

            obj.value[1] = values[1] | EX_CLOSED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You close {obj_name}."

        # Container
        if item_type == ItemType.CONTAINER:
            if not (values[1] & ContainerFlag.CLOSEABLE):
                return "You can't do that."
            if values[1] & ContainerFlag.CLOSED:
                return "It's already closed."

            obj.value[1] = values[1] | ContainerFlag.CLOSED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You close {obj_name}."

        return "That's not a container."

    # Check for door
    door, error = _find_door(char, args)
    if door is None:
        return error

    exits = getattr(room, "exits", [])
    pexit = exits[door]
    exit_info = getattr(pexit, "exit_info", 0)

    if exit_info & EX_CLOSED:
        return "It's already closed."

    # Close this side
    pexit.exit_info = exit_info | EX_CLOSED

    # Close the other side
    to_room = getattr(pexit, "to_room", None)
    if to_room:
        rev_dir = _REV_DIR.get(Direction(door))
        if rev_dir is not None:
            rev_exits = getattr(to_room, "exits", [])
            if rev_exits and rev_dir < len(rev_exits) and rev_exits[rev_dir]:
                pexit_rev = rev_exits[rev_dir]
                rev_to = getattr(pexit_rev, "to_room", None)
                if rev_to is room:
                    rev_info = getattr(pexit_rev, "exit_info", 0)
                    pexit_rev.exit_info = rev_info | EX_CLOSED

    return "Ok."


def _has_key(char: Character, key_vnum: int) -> bool:
    """Check if character has the required key.

    ROM Reference: src/act_move.c has_key() — scans ch->carrying for an object
    whose pIndexData->vnum matches. In QuickMUD the canonical inventory list is
    `Character.inventory` and Object instances expose vnum via `prototype.vnum`.
    """
    for obj in getattr(char, "inventory", []) or []:
        proto = getattr(obj, "prototype", None)
        proto_vnum = getattr(proto, "vnum", None) if proto is not None else None
        if proto_vnum == key_vnum:
            return True
        if getattr(obj, "vnum", None) == key_vnum:
            return True
    return False


def do_lock(char: Character, args: str) -> str:
    """
    Lock a door, container, or portal.

    ROM Reference: src/act_move.c do_lock (lines 571-705)

    Usage: lock <door/container/portal/direction>
    """
    args = args.strip()

    if not args:
        return "Lock what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # Check for object first (portal or container)
    obj = get_obj_here(char, args)
    if obj:
        item_type = getattr(obj, "item_type", 0)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])

        # Portal (ROM C lines 588-624)
        if item_type == ItemType.PORTAL:
            if not (values[1] & EX_ISDOOR) or (values[1] & EX_NOCLOSE):
                return "You can't do that."
            if not (values[1] & EX_CLOSED):
                return "It's not closed."
            if values[4] < 0 or (values[1] & EX_NOLOCK):
                return "It can't be locked."
            if not _has_key(char, values[4]):
                return "You lack the key."
            if values[1] & EX_LOCKED:
                return "It's already locked."

            obj.value[1] = values[1] | EX_LOCKED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You lock {obj_name}."

        # Container (ROM C lines 627-656)
        if item_type == ItemType.CONTAINER:
            if not (values[1] & ContainerFlag.CLOSEABLE):
                return "You can't do that."
            if not (values[1] & ContainerFlag.CLOSED):
                return "It's not closed."
            if values[2] <= 0:  # No key defined
                return "It can't be locked."
            if not _has_key(char, values[2]):
                return "You lack the key."
            if values[1] & ContainerFlag.LOCKED:
                return "It's already locked."

            obj.value[1] = values[1] | ContainerFlag.LOCKED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You lock {obj_name}."

        return "That's not a container."

    # Check for door (ROM C lines 659-702)
    door, error = _find_door(char, args)
    if door is None:
        return error

    exits = getattr(room, "exits", [])
    pexit = exits[door]
    exit_info = getattr(pexit, "exit_info", 0)
    key_vnum = getattr(pexit, "key", 0)

    if not (exit_info & EX_CLOSED):
        return "It's not closed."
    if key_vnum <= 0:
        return "It can't be locked."
    if not _has_key(char, key_vnum):
        return "You lack the key."
    if exit_info & EX_LOCKED:
        return "It's already locked."

    # Lock this side
    pexit.exit_info = exit_info | EX_LOCKED

    # Lock the other side
    to_room = getattr(pexit, "to_room", None)
    if to_room:
        rev_dir = _REV_DIR.get(Direction(door))
        if rev_dir is not None:
            rev_exits = getattr(to_room, "exits", [])
            if rev_exits and rev_dir < len(rev_exits) and rev_exits[rev_dir]:
                pexit_rev = rev_exits[rev_dir]
                rev_to = getattr(pexit_rev, "to_room", None)
                if rev_to is room:
                    rev_info = getattr(pexit_rev, "exit_info", 0)
                    pexit_rev.exit_info = rev_info | EX_LOCKED

    return "*Click*"


def do_unlock(char: Character, args: str) -> str:
    """
    Unlock a door, container, or portal.

    ROM Reference: src/act_move.c do_unlock (lines 706-840)

    Usage: unlock <door/container/portal/direction>
    """
    args = args.strip()

    if not args:
        return "Unlock what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # Check for object first (portal or container)
    obj = get_obj_here(char, args)
    if obj:
        item_type = getattr(obj, "item_type", 0)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])

        # Portal (ROM C lines 723-758)
        if item_type == ItemType.PORTAL:
            if not (values[1] & EX_ISDOOR):
                return "You can't do that."
            if not (values[1] & EX_CLOSED):
                return "It's not closed."
            if values[4] < 0:
                return "It can't be unlocked."
            if not _has_key(char, values[4]):
                return "You lack the key."
            if not (values[1] & EX_LOCKED):
                return "It's already unlocked."

            obj.value[1] = values[1] & ~EX_LOCKED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You unlock {obj_name}."

        # Container (ROM C lines 761-791)
        if item_type == ItemType.CONTAINER:
            if not (values[1] & ContainerFlag.CLOSEABLE):
                return "You can't do that."
            if not (values[1] & ContainerFlag.CLOSED):
                return "It's not closed."
            if values[2] <= 0:  # No key defined
                return "It can't be unlocked."
            if not _has_key(char, values[2]):
                return "You lack the key."
            if not (values[1] & ContainerFlag.LOCKED):
                return "It's already unlocked."

            obj.value[1] = values[1] & ~ContainerFlag.LOCKED
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You unlock {obj_name}."

        return "That's not a container."

    # Check for door (ROM C lines 794-837)
    door, error = _find_door(char, args)
    if door is None:
        return error

    exits = getattr(room, "exits", [])
    pexit = exits[door]
    exit_info = getattr(pexit, "exit_info", 0)
    key_vnum = getattr(pexit, "key", 0)

    if not (exit_info & EX_CLOSED):
        return "It's not closed."
    if key_vnum <= 0:
        return "It can't be unlocked."
    if not _has_key(char, key_vnum):
        return "You lack the key."
    if not (exit_info & EX_LOCKED):
        return "It's already unlocked."

    # Unlock this side
    pexit.exit_info = exit_info & ~EX_LOCKED

    # Unlock the other side
    to_room = getattr(pexit, "to_room", None)
    if to_room:
        rev_dir = _REV_DIR.get(Direction(door))
        if rev_dir is not None:
            rev_exits = getattr(to_room, "exits", [])
            if rev_exits and rev_dir < len(rev_exits) and rev_exits[rev_dir]:
                pexit_rev = rev_exits[rev_dir]
                rev_to = getattr(pexit_rev, "to_room", None)
                if rev_to is room:
                    rev_info = getattr(pexit_rev, "exit_info", 0)
                    pexit_rev.exit_info = rev_info & ~EX_LOCKED

    return "*Click*"


def do_pick(char: Character, args: str) -> str:
    """
    Pick a lock on a door, container, or portal.

    ROM Reference: src/act_move.c do_pick (lines 841-994)

    Usage: pick <door/container/portal/direction>
    """
    from mud.utils.rng_mm import number_percent

    args = args.strip()

    if not args:
        return "Pick what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # Check for pick skill
    skill_level = 0
    skills = getattr(char, "skills", {})
    if "pick lock" in skills:
        skill_level = skills["pick lock"]
    elif "pick" in skills:
        skill_level = skills["pick"]

    if skill_level <= 0:
        return "You don't know how to pick locks."

    # WAIT_STATE (ROM C line 856)
    # TODO: Implement wait state delay based on skill_table[gsn_pick_lock].beats
    char.wait = getattr(char, "wait", 0) + 24  # Placeholder: 24 pulses = 1 round

    # Guard detection (ROM C lines 858-867)
    people = getattr(room, "people", [])
    level = getattr(char, "level", 1)
    for gch in people:
        is_npc = getattr(gch, "is_npc", False)
        position = getattr(gch, "position", 5)  # 5 = STANDING
        gch_level = getattr(gch, "level", 1)

        if is_npc and position >= 5 and (level + 5) < gch_level:  # AWAKE check
            gch_name = getattr(gch, "short_descr", None) or getattr(gch, "name", "someone")
            return f"{gch_name} is standing too close to the lock."

    # Skill check (ROM C lines 869-874)
    is_npc = getattr(char, "is_npc", False)
    if not is_npc and number_percent() > skill_level:
        # TODO: Implement check_improve(ch, gsn_pick_lock, FALSE, 2)
        return "You failed."

    # Check for object first (portal or container)
    obj = get_obj_here(char, args)
    if obj:
        item_type = getattr(obj, "item_type", 0)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])

        # Portal (ROM C lines 879-910)
        if item_type == ItemType.PORTAL:
            if not (values[1] & EX_ISDOOR):
                return "You can't do that."
            if not (values[1] & EX_CLOSED):
                return "It's not closed."
            if values[4] < 0:
                return "It can't be unlocked."
            if not (values[1] & EX_LOCKED):
                return "It's already unlocked."
            if values[1] & EX_PICKPROOF:
                return "You failed."

            obj.value[1] = values[1] & ~EX_LOCKED
            # TODO: Implement check_improve(ch, gsn_pick_lock, TRUE, 2)
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You pick the lock on {obj_name}."

        # Container (ROM C lines 916-947)
        if item_type == ItemType.CONTAINER:
            if not (values[1] & ContainerFlag.CLOSED):
                return "It's not closed."
            if values[2] < 0:  # No lock
                return "It can't be unlocked."
            if not (values[1] & ContainerFlag.LOCKED):
                return "It's already unlocked."
            if values[1] & ContainerFlag.PICKPROOF:
                return "You failed."

            obj.value[1] = values[1] & ~ContainerFlag.LOCKED
            # TODO: Implement check_improve(ch, gsn_pick_lock, TRUE, 2)
            obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it")
            return f"You pick the lock on {obj_name}."

        return "That's not a container."

    # Check for door (ROM C lines 950-991)
    door, error = _find_door(char, args)
    if door is None:
        return error

    exits = getattr(room, "exits", [])
    pexit = exits[door]
    exit_info = getattr(pexit, "exit_info", 0)
    key_vnum = getattr(pexit, "key", 0)

    # Immortal check (ROM C lines 958, 963, 973)
    trust = getattr(char, "trust", 0)
    is_immortal = trust >= 51  # LEVEL_HERO threshold

    if not (exit_info & EX_CLOSED) and not is_immortal:
        return "It's not closed."
    if key_vnum < 0 and not is_immortal:
        return "It can't be picked."
    if not (exit_info & EX_LOCKED):
        return "It's already unlocked."
    if (exit_info & EX_PICKPROOF) and not is_immortal:
        return "You failed."

    # Unlock this side
    pexit.exit_info = exit_info & ~EX_LOCKED

    # TODO: Implement check_improve(ch, gsn_pick_lock, TRUE, 2)

    # Unlock the other side (ROM C lines 984-990)
    to_room = getattr(pexit, "to_room", None)
    if to_room:
        rev_dir = _REV_DIR.get(Direction(door))
        if rev_dir is not None:
            rev_exits = getattr(to_room, "exits", [])
            if rev_exits and rev_dir < len(rev_exits) and rev_exits[rev_dir]:
                pexit_rev = rev_exits[rev_dir]
                rev_to = getattr(pexit_rev, "to_room", None)
                if rev_to is room:
                    rev_info = getattr(pexit_rev, "exit_info", 0)
                    pexit_rev.exit_info = rev_info & ~EX_LOCKED

    return "*Click*"
