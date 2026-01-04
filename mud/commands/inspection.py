from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Direction
from mud.world.look import dir_names, look
from mud.world.vision import can_see_character, describe_character


def do_scan(char: Character, args: str = "") -> str:
    """ROM-like scan output with distances and optional direction.

    - No arg: list current room (depth 0) and adjacent rooms (depth 1) in N,E,S,W,Up,Down order.
    - With direction: follow exits up to depth 3 and list visible characters per room.
    """
    if not char.room:
        return "You see nothing."

    order = [
        Direction.NORTH,
        Direction.EAST,
        Direction.SOUTH,
        Direction.WEST,
        Direction.UP,
        Direction.DOWN,
    ]
    dir_name = {
        Direction.NORTH: "north",
        Direction.EAST: "east",
        Direction.SOUTH: "south",
        Direction.WEST: "west",
        Direction.UP: "up",
        Direction.DOWN: "down",
    }
    distance = [
        "right here.",
        "nearby to the %s.",
        "not far %s.",
        "off in the distance %s.",
    ]

    def _get_exit(room, direction: Direction):  # type: ignore[valid-type]
        if not room:
            return None
        exits = getattr(room, "exits", None)
        if not exits:
            return None
        idx = int(direction)
        if isinstance(exits, dict):
            return exits.get(idx) or exits.get(direction)
        if 0 <= idx < len(exits):
            return exits[idx]
        return None

    def list_room(room, depth: int, door: int) -> list[str]:
        lines: list[str] = []
        if not room:
            return lines
        for p in room.people:
            if p is char:
                continue
            if not can_see_character(char, p):
                continue
            who = describe_character(char, p)
            if depth == 0:
                lines.append(f"{who}, {distance[0]}")
            else:
                dn = dir_name[Direction(door)]
                lines.append(f"{who}, {distance[depth] % dn}")
        return lines

    s = args.strip().lower()
    if not s:
        lines: list[str] = ["Looking around you see:"]
        # current room
        lines += list_room(char.room, 0, -1)
        # each direction at depth 1
        for d in order:
            ex = _get_exit(char.room, d)
            to_room = ex.to_room if ex else None
            lines += list_room(to_room, 1, int(d))
        if len(lines) == 1:
            lines.append("No one is nearby.")
        return "\n".join(lines)

    # Directional scan up to depth 3
    token_map = {
        "n": Direction.NORTH,
        "north": Direction.NORTH,
        "e": Direction.EAST,
        "east": Direction.EAST,
        "s": Direction.SOUTH,
        "south": Direction.SOUTH,
        "w": Direction.WEST,
        "west": Direction.WEST,
        "u": Direction.UP,
        "up": Direction.UP,
        "d": Direction.DOWN,
        "down": Direction.DOWN,
    }
    if s not in token_map:
        return "Which way do you want to scan?"
    d = token_map[s]
    dir_str = dir_name[d]
    lines = [f"Looking {dir_str} you see:"]
    scan_room = char.room
    for depth in (1, 2, 3):
        ex = _get_exit(scan_room, d)
        scan_room = ex.to_room if ex else None
        if not scan_room:
            break
        lines += list_room(scan_room, depth, int(d))
    if len(lines) == 1:
        lines.append("Nothing of note.")
    return "\n".join(lines)


def do_look(char: Character, args: str = "") -> str:
    """
    Look at room, character, object, or direction.

    ROM Reference: src/act_info.c do_look

    Usage:
    - look (show room)
    - look <character> (examine character)
    - look <object> (examine object)
    - look in <container> (show container contents)
    - look <direction> (peek through exit)
    """
    return look(char, args)


def do_exits(char: Character, args: str = "") -> str:
    """
    List obvious exits from the current room (ROM-style).

    ROM Reference: src/act_info.c do_exits (lines 1393-1451)

    Supports:
    - exits (detailed format with room names)
    - exits auto (compact format for auto-exit display)

    Features:
    - Blindness check (blind characters see nothing)
    - Closed door hiding (exits with closed doors are hidden)
    - Room permission checks (forbidden rooms hidden)
    - Immortal extras (room vnums in header and per exit)
    - Dark room handling ("Too dark to tell" message)
    - Auto-exit mode (compact format: [Exits: north south])

    NOTE: Unlike movement commands, do_exits shows dark rooms as "Too dark to tell"
    rather than hiding them entirely. ROM C can_see_room() does NOT check darkness,
    only permission flags (handler.c lines 2590-2611).
    """
    from mud.models.constants import AffectFlag, EX_CLOSED, MAX_LEVEL, RoomFlag
    from mud.world.vision import room_is_dark

    # ROM: check_blind - blind characters cannot see exits
    # ROM C: if (IS_AFFECTED (ch, AFF_BLIND)) { send_to_char ("You can't see a thing!\n\r", ch); return FALSE; }
    if char.has_affect(AffectFlag.BLIND):
        return "You can't see a thing!"

    if not char.room:
        return "Obvious exits: none."

    # ROM: fAuto = !str_cmp (argument, "auto")
    auto_mode = args.strip().lower() == "auto"

    # Build header based on mode and immortal status
    if auto_mode:
        # ROM: sprintf (buf, "{o[Exits:")
        output = "{o[Exits:"
    elif char.is_immortal():
        # ROM: sprintf (buf, "Obvious exits from room %d:\n\r", ch->in_room->vnum)
        output = f"Obvious exits from room {char.room.vnum}:\n"
    else:
        # ROM: sprintf (buf, "Obvious exits:\n\r")
        output = "Obvious exits:\n"

    # Iterate through all 6 directions (N, E, S, W, U, D)
    # ROM: for (door = 0; door <= 5; door++)
    exits = getattr(char.room, "exits", None)
    if not exits:
        if auto_mode:
            return "{o[Exits: none]{x\n"
        else:
            return output + "None.\n"

    found_exits = []

    # Helper function: ROM C can_see_room (handler.c lines 2590-2611)
    # Note: This does NOT check darkness, only permission flags
    def _can_see_room_permissions(room) -> bool:
        """Check if character has permission to see room (no darkness check)."""
        flags = int(getattr(room, "room_flags", 0) or 0)
        trust = char.trust if char.trust else char.level

        if flags & int(RoomFlag.ROOM_IMP_ONLY) and trust < MAX_LEVEL:
            return False
        if flags & int(RoomFlag.ROOM_GODS_ONLY) and not char.is_immortal():
            return False
        if flags & int(RoomFlag.ROOM_HEROES_ONLY) and not char.is_immortal():
            return False
        if flags & int(RoomFlag.ROOM_NEWBIES_ONLY) and trust > 5 and not char.is_immortal():
            return False

        room_clan = int(getattr(room, "clan", 0) or 0)
        char_clan = int(getattr(char, "clan", 0) or 0)
        if room_clan and not char.is_immortal() and room_clan != char_clan:
            return False

        return True

    for direction in (Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST, Direction.UP, Direction.DOWN):
        door_idx = int(direction)

        # Get exit for this direction
        if isinstance(exits, dict):
            pexit = exits.get(door_idx) or exits.get(direction)
        elif 0 <= door_idx < len(exits):
            pexit = exits[door_idx]
        else:
            pexit = None

        # ROM: Check exit validity and visibility
        # if ((pexit = ch->in_room->exit[door]) != NULL
        #     && pexit->u1.to_room != NULL
        #     && can_see_room (ch, pexit->u1.to_room)  <-- ONLY checks permissions, NOT darkness
        #     && !IS_SET (pexit->exit_info, EX_CLOSED))
        if (
            pexit is not None
            and pexit.to_room is not None
            and _can_see_room_permissions(pexit.to_room)  # Permission check only
            and not (pexit.exit_info & EX_CLOSED)
        ):
            dir_name = dir_names[direction]

            if auto_mode:
                # ROM: strcat (buf, " "); strcat (buf, dir_name[door]);
                found_exits.append(dir_name)
            else:
                # ROM: sprintf (buf + strlen (buf), "%-5s - %s",
                #              capitalize (dir_name[door]),
                #              room_is_dark (pexit->u1.to_room)
                #              ? "Too dark to tell" : pexit->u1.to_room->name)
                dir_capitalized = dir_name.capitalize()

                # Check if target room is dark (SEPARATE from permission check)
                if room_is_dark(pexit.to_room):
                    room_desc = "Too dark to tell"
                else:
                    room_desc = pexit.to_room.name or "Unknown"

                exit_line = f"{dir_capitalized:5s} - {room_desc}"

                # ROM: if (IS_IMMORTAL (ch))
                #          sprintf (buf + strlen (buf), " (room %d)\n\r", pexit->u1.to_room->vnum)
                if char.is_immortal():
                    exit_line += f" (room {pexit.to_room.vnum})"

                found_exits.append(exit_line)

    # Format output based on mode
    if auto_mode:
        # ROM: if (!found) strcat (buf, fAuto ? " none" : "None.\n\r")
        if found_exits:
            output += " " + " ".join(found_exits)
        else:
            output += " none"
        # ROM: if (fAuto) strcat (buf, "]{x\n\r")
        output += "]{x\n"
    else:
        if found_exits:
            output += "\n".join(found_exits) + "\n"
        else:
            # ROM: "None.\n\r"
            output += "None.\n"

    return output
