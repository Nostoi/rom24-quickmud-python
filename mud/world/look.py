from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Direction, Position
from mud.world.vision import can_see_character, describe_character

# mirroring ROM src/act_info.c show_char_to_char_0 — buf[0] = UPPER(buf[0]) and
# position suffixes appended when a mob is not at its start/default position.
# victim->on == NULL path only; the furniture-object branch is not yet ported.
_POSITION_SUFFIX: dict[Position, str] = {
    Position.DEAD: " is DEAD!!",
    Position.MORTAL: " is mortally wounded.",
    Position.INCAP: " is incapacitated.",
    Position.STUNNED: " is lying here stunned.",
    Position.SLEEPING: " is sleeping here.",
    Position.RESTING: " is resting here.",
    Position.SITTING: " is sitting here.",
    Position.STANDING: " is here.",
    # FIGHTING: handled separately (target-aware)
}


def _room_occupant_line(observer: Character, victim) -> str:
    """Render a room-list occupant — ROM src/act_info.c show_char_to_char_0.

    An NPC whose position equals its start/default position and which has a
    non-empty long_descr is listed by that long_descr (with affect auras
    prefixed), e.g. "Hassan is here, waiting to dispense some justice."
    Otherwise show PERS(victim) + a position suffix ("is resting here.", etc.).
    """
    prefixes = []
    if hasattr(victim, "has_affect"):
        if victim.has_affect(AffectFlag.SANCTUARY):
            prefixes.append("(White Aura)")
        if victim.has_affect(AffectFlag.FAERIE_FIRE):
            prefixes.append("(Pink Aura)")
    prefix = (" ".join(prefixes) + " ") if prefixes else ""

    long_descr = getattr(victim, "long_descr", None)
    # ROM uses start_pos for the long_descr gate; Python stores default_pos (same
    # value for normally-spawned mobs).  Fall back to start_pos if present.
    ref_pos = getattr(victim, "start_pos", getattr(victim, "default_pos", None))
    if getattr(victim, "is_npc", False) and long_descr and getattr(victim, "position", None) == ref_pos:
        return prefix + str(long_descr).rstrip("\r\n")

    pers = describe_character(observer, victim)
    position = getattr(victim, "position", None)
    fighting = getattr(victim, "fighting", None)
    if position == Position.FIGHTING:
        # mirroring ROM src/act_info.c:404-417 show_char_to_char_0 POS_FIGHTING
        if fighting is None:
            fight_str = "thin air??"
        elif fighting is observer:
            fight_str = "YOU!"
        elif getattr(victim, "room", None) is getattr(fighting, "room", object()):
            fight_str = describe_character(observer, fighting) + "."
        else:
            fight_str = "someone who left??"
        line = prefix + pers + " is here, fighting " + fight_str
    else:
        suffix = _POSITION_SUFFIX.get(position, "") if position is not None else ""
        line = prefix + pers + suffix
    # mirroring ROM src/act_info.c:421 buf[0] = UPPER(buf[0])
    return line[0].upper() + line[1:] if line else line


def _ed_fields(ed) -> tuple[str | None, str | None]:
    """Return (keyword, description) for an EXTRA_DESCR entry.

    JSON-loaded prototypes store extra_descr as raw dicts (per ObjIndex's
    `list[dict]` annotation); runtime ObjectData/ExtraDescr instances expose
    them as attributes. Accept both shapes.
    """
    if isinstance(ed, dict):
        return ed.get("keyword"), ed.get("description")
    return getattr(ed, "keyword", None), getattr(ed, "description", None)


dir_names = {
    Direction.NORTH: "north",
    Direction.EAST: "east",
    Direction.SOUTH: "south",
    Direction.WEST: "west",
    Direction.UP: "up",
    Direction.DOWN: "down",
}


def look(char: Character, args: str = "") -> str:
    """
    Look command handler - ROM src/act_info.c do_look

    Supports:
    - look (show room)
    - look <character> (examine character)
    - look <object> (examine object)
    - look in <container> (show container contents)
    - look <direction> (peek through exit)
    """
    from mud.world.char_find import get_char_room
    from mud.world.obj_find import get_obj_carry, get_obj_here

    room = char.room
    if not room:
        return "You are floating in a void..."

    # Check position - ROM src/act_info.c lines 1053-1063
    position = getattr(char, "position", Position.STANDING)
    if position < Position.SLEEPING:
        return "You can't see anything but stars!"
    if position == Position.SLEEPING:
        return "You can't see anything, you're sleeping!"

    # Check blind - ROM src/act_info.c lines 1065-1066
    from mud.world.vision import check_blind

    if not check_blind(char):
        return "You can't see a thing!"

    # Check dark room - ROM src/act_info.c lines 1068-1074
    from mud.world.vision import room_is_dark

    is_npc = getattr(char, "is_npc", False)
    # TODO: Add PLR_HOLYLIGHT check when PlayerFlag is accessible
    if not is_npc and room_is_dark(room):
        lines = ["It is pitch black ..."]
        for occupant in room.people:
            if occupant is char:
                continue
            if not can_see_character(char, occupant):
                continue
            # mirroring ROM src/act_info.c show_char_to_char: when can_see is
            # True even in a dark room, show_char_to_char_0 is called (same as
            # the lit-room path) — not just the PERS name.
            lines.append(_room_occupant_line(char, occupant))
        return "\n".join(lines)

    # Parse arguments
    args = args.strip()
    if not args or args.lower() == "auto":
        # 'look' or 'look auto' - show room
        return _look_room(char, room)

    # Check for "look in <container>"
    parts = args.split(None, 1)
    if parts[0].lower() in ("i", "in", "on") and len(parts) > 1:
        return _look_in(char, parts[1])

    # Check for direction
    direction = _parse_direction(args)
    if direction is not None:
        return _look_direction(char, room, direction)

    # Try to find a character in the room
    victim = get_char_room(char, args)
    if victim:
        return _look_char(char, victim)

    # Try to find an object in the room or inventory
    obj = get_obj_here(char, args)
    if obj:
        return _look_obj(char, obj)

    # Check inventory
    obj = get_obj_carry(char, args)
    if obj:
        return _look_obj(char, obj)

    # Check extra descriptions in room
    for ed in getattr(room, "extra_descr", []):
        keyword, description = _ed_fields(ed)
        if keyword and args.lower() in keyword.lower().split():
            return description or "You see nothing special."

    return "You do not see that here."


def _look_room(char: Character, room) -> str:
    """Show room description - ROM src/act_info.c lines 1081-1116"""
    lines = []

    # Room name with optional vnum for immortals/builders - ROM src/act_info.c lines 1088-1094
    from mud.models.constants import LEVEL_IMMORTAL, PlayerFlag

    level = getattr(char, "level", 1)
    act_flags = getattr(char, "act", 0)
    is_immortal = level >= LEVEL_IMMORTAL
    has_holylight = act_flags & PlayerFlag.HOLYLIGHT
    is_builder = False  # TODO: Implement IS_BUILDER check when area builders are added

    room_name = room.name or ""
    if (is_immortal and (getattr(char, "is_npc", False) or has_holylight)) or is_builder:
        # Show room vnum for immortals with holylight or builders
        vnum = getattr(room, "vnum", 0)
        lines.append(f"[Room {vnum}] {room_name}")
    else:
        lines.append(room_name)

    # Room description - ROM src/act_info.c lines 1098-1105
    # Skip description if COMM_BRIEF is set
    from mud.models.constants import CommFlag

    comm_flags = getattr(char, "comm", 0)
    if not (comm_flags & CommFlag.BRIEF):
        room_desc = room.description or ""
        lines.append(room_desc)

    # Objects in room — ROM src/act_info.c:1106
    # show_list_to_char(ch->in_room->contents, ch, FALSE, FALSE)
    # Uses f_short=False (ground description), f_show_nothing=False (no "Nothing."),
    # can_see_obj visibility filter, and COMBINE coalescing for NPC/COMBINE viewers.
    from mud.utils.act import show_list_to_char

    obj_text = show_list_to_char(room.contents, char, f_short=False, f_show_nothing=False)
    if obj_text:
        lines.append(obj_text.rstrip("\n"))

    # Characters in room — ROM appends raw character lines via show_char_to_char.
    for occupant in room.people:
        if occupant is char:
            continue
        if not can_see_character(char, occupant):
            continue
        lines.append(_room_occupant_line(char, occupant))

    result = "\n".join(lines).strip()

    # AUTOEXIT integration - ROM src/act_info.c lines 1107-1111
    # Auto-show exits if PLR_AUTOEXIT is set
    from mud.commands.inspection import do_exits
    from mud.models.constants import PlayerFlag

    if not getattr(char, "is_npc", False) and (act_flags & PlayerFlag.AUTOEXIT):
        # Call do_exits with "auto" to get concise exit display
        exit_text = do_exits(char, "auto")
        if exit_text:
            result += "\n" + exit_text

    return result


def _look_char(char: Character, victim: Character) -> str:
    """Show character description - ROM src/act_info.c show_char_to_char_1"""
    lines = []

    # Show description
    desc = getattr(victim, "description", None)
    if desc:
        lines.append(desc)
    else:
        short = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
        lines.append(f"You see nothing special about {short}.")

    # Show health condition - ROM health_str equivalent
    max_hit = getattr(victim, "max_hit", 100) or 100
    hit = getattr(victim, "hit", max_hit)
    percent = (hit * 100) // max_hit if max_hit > 0 else 100

    short = getattr(victim, "short_descr", None) or getattr(victim, "name", "Someone")
    if percent >= 100:
        condition = f"{short} is in excellent condition."
    elif percent >= 90:
        condition = f"{short} has a few scratches."
    elif percent >= 75:
        condition = f"{short} has some small wounds and bruises."
    elif percent >= 50:
        condition = f"{short} has quite a few wounds."
    elif percent >= 30:
        condition = f"{short} has some big nasty wounds and scratches."
    elif percent >= 15:
        condition = f"{short} looks pretty hurt."
    elif percent >= 0:
        condition = f"{short} is in awful condition."
    else:
        condition = f"{short} is bleeding to death."
    lines.append(condition)

    # Show equipment if visible
    equipment = _show_equipment(victim)
    if equipment:
        lines.append(f"\n{short} is using:")
        lines.append(equipment)

    return "\n".join(lines)


def _show_equipment(char: Character) -> str:
    """Show equipped items - ROM show_char_to_char_1"""
    from mud.models.constants import WearLocation

    wear_names = {
        WearLocation.LIGHT: "<used as light>     ",
        WearLocation.FINGER_L: "<worn on finger>    ",
        WearLocation.FINGER_R: "<worn on finger>    ",
        WearLocation.NECK_1: "<worn around neck>  ",
        WearLocation.NECK_2: "<worn around neck>  ",
        WearLocation.BODY: "<worn on torso>     ",
        WearLocation.HEAD: "<worn on head>      ",
        WearLocation.LEGS: "<worn on legs>      ",
        WearLocation.FEET: "<worn on feet>      ",
        WearLocation.HANDS: "<worn on hands>     ",
        WearLocation.ARMS: "<worn on arms>      ",
        WearLocation.SHIELD: "<worn as shield>    ",
        WearLocation.ABOUT: "<worn about body>   ",
        WearLocation.WAIST: "<worn about waist>  ",
        WearLocation.WRIST_L: "<worn around wrist> ",
        WearLocation.WRIST_R: "<worn around wrist> ",
        WearLocation.WIELD: "<wielded>           ",
        WearLocation.HOLD: "<held>              ",
        WearLocation.FLOAT: "<floating nearby>   ",
    }

    lines = []
    equipped = getattr(char, "equipped", {})
    if isinstance(equipped, dict):
        for loc, obj in equipped.items():
            if obj:
                loc_name = wear_names.get(loc, "<unknown>           ")
                obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
                lines.append(f"  {loc_name}{obj_name}")

    return "\n".join(lines)


def _look_obj(char: Character, obj) -> str:
    """Show object description - ROM src/act_info.c lines 1217-1245"""
    lines = []

    desc = getattr(obj, "description", None)
    if desc:
        lines.append(desc)
    else:
        short = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
        lines.append(f"You see nothing special about {short}.")

    # Show extra descriptions - check both object and prototype
    # ROM src/act_info.c lines 1221-1235
    # First check object's own extra_descr
    for ed in getattr(obj, "extra_descr", []):
        _, description = _ed_fields(ed)
        if description:
            lines.append(description)
            break
    else:
        # If no extra_descr found, check prototype (pIndexData->extra_descr)
        prototype = getattr(obj, "prototype", None)
        if prototype:
            for ed in getattr(prototype, "extra_descr", []):
                _, description = _ed_fields(ed)
                if description:
                    lines.append(description)
                    break

    return "\n".join(lines)


def _look_in(char: Character, args: str) -> str:
    """Look inside a container - ROM src/act_info.c lines 1070-1130"""
    from mud.models.constants import LIQUID_TABLE, ContainerFlag, ItemType
    from mud.utils.act import capitalize_act_line
    from mud.world.obj_find import get_obj_here

    obj = get_obj_here(char, args)
    if not obj:
        return "You do not see that here."

    item_type = getattr(obj, "item_type", 0)

    if item_type == ItemType.DRINK_CON:
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        if len(value) < 3:
            return "It is empty."
        if value[1] <= 0:
            return "It is empty."
        if value[0] > 0:
            percent = value[1] * 100 // value[0]
            if percent < 25:
                amount = "less than half-"
            elif percent < 75:
                amount = "about half-"
            else:
                amount = "more than half-"
        else:
            amount = ""
        liquid_index = int(value[2]) if len(value) > 2 else 0
        if 0 <= liquid_index < len(LIQUID_TABLE):
            liquid_color = LIQUID_TABLE[liquid_index].color
        else:
            liquid_color = "clear"
        return f"It's {amount}filled with  a {liquid_color} liquid."

    if item_type in (ItemType.CONTAINER, ItemType.CORPSE_NPC, ItemType.CORPSE_PC):
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        if len(value) > 1 and (value[1] & int(ContainerFlag.CLOSED)):
            return "It is closed."

        # ROM src/act_info.c:1166-1167 — `act("$p holds:")` then
        # `show_list_to_char(obj->contains, ch, TRUE, TRUE)`. `act_new` caps the
        # header's first visible char (INV-029 ACT-CAP), so "a bag" → "A bag
        # holds:". `show_list_to_char` then formats the contents: for NPC or
        # COMM_COMBINE viewers, duplicates are coalesced with `(%2d) ` counts or
        # 5-space padding; for non-COMBINE PCs, items are listed with no indent.
        # FINDING-022: the old code always prepended 2-space indent, matching
        # neither the no-indent PC path nor the 5-space COMBINE path.
        short = getattr(obj, "short_descr", None) or "It"
        header = capitalize_act_line(f"{short} holds:")

        contents = getattr(obj, "contains", None) or getattr(obj, "contained_items", [])
        from mud.utils.act import show_list_to_char

        body = show_list_to_char(contents, char, f_short=True, f_show_nothing=True)
        # show_list_to_char returns trailing \n; strip it since we join with \n
        return header + "\n" + body.rstrip("\n")

    return "That is not a container."


def _look_direction(char: Character, room, direction: int) -> str:
    """Look in a direction - ROM src/act_info.c lines 1268-1312"""
    exits = getattr(room, "exits", [])
    if direction >= len(exits) or not exits[direction]:
        return "Nothing special there."

    exit_obj = exits[direction]
    lines = []

    # Show exit description if present
    desc = getattr(exit_obj, "description", None)
    if desc:
        lines.append(desc)

    # Show door status - ROM src/act_info.c lines 1298-1309
    keyword = getattr(exit_obj, "keyword", None)
    exit_info = getattr(exit_obj, "exit_info", 0)

    # EX_CLOSED = 1, EX_ISDOOR = 2
    EX_ISDOOR = 2
    EX_CLOSED = 1

    if keyword and keyword.strip():
        if exit_info & EX_CLOSED:
            lines.append(f"The {keyword} is closed.")
        elif exit_info & EX_ISDOOR:
            lines.append(f"The {keyword} is open.")

    if lines:
        return "\n".join(lines)
    return "Nothing special there."


def _parse_direction(arg: str) -> int | None:
    """Parse direction argument"""
    dir_map = {
        "n": 0,
        "north": 0,
        "e": 1,
        "east": 1,
        "s": 2,
        "south": 2,
        "w": 3,
        "west": 3,
        "u": 4,
        "up": 4,
        "d": 5,
        "down": 5,
    }
    return dir_map.get(arg.lower())
