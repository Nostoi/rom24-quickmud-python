from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Direction, Position
from mud.world.vision import can_see_character, describe_character

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
    from mud.world.obj_find import get_obj_here, get_obj_carry

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
    from mud.rom_api import check_blind

    if not check_blind(char):
        return "You can't see anything!"

    # Check dark room - ROM src/act_info.c lines 1068-1074
    from mud.world.vision import room_is_dark

    is_npc = getattr(char, "is_npc", False)
    # TODO: Add PLR_HOLYLIGHT check when PlayerFlag is accessible
    if not is_npc and room_is_dark(room):
        lines = ["It is pitch black ..."]
        # Still show characters in dark rooms (infravision equivalent)
        visible_characters: list[str] = []
        for occupant in room.people:
            if occupant is char:
                continue
            if not can_see_character(char, occupant):
                continue
            visible_characters.append(describe_character(char, occupant))
        if visible_characters:
            lines.append("Characters: " + ", ".join(visible_characters))
        return "\n".join(lines)

    if not check_blind(char):
        return "You can't see anything!"

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
        keyword = getattr(ed, "keyword", None)
        if keyword and args.lower() in keyword.lower().split():
            return ed.description or "You see nothing special."

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

    # Exits
    exit_list = [dir_names[Direction(i)] for i, ex in enumerate(room.exits) if ex]
    if exit_list:
        lines.append(f"[Exits: {' '.join(exit_list)}]")

    # Objects in room
    if room.contents:
        lines.append("Objects: " + ", ".join(obj.short_descr or obj.name or "object" for obj in room.contents))

    # Characters in room
    visible_characters: list[str] = []
    for occupant in room.people:
        if occupant is char:
            continue
        if not can_see_character(char, occupant):
            continue
        visible_characters.append(describe_character(char, occupant))
    if visible_characters:
        lines.append("Characters: " + ", ".join(visible_characters))

    result = "\n".join(lines).strip()

    # AUTOEXIT integration - ROM src/act_info.c lines 1107-1111
    # Auto-show exits if PLR_AUTOEXIT is set
    from mud.models.constants import PlayerFlag
    from mud.commands.inspection import do_exits

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
        if ed.description:
            lines.append(ed.description)
            break
    else:
        # If no extra_descr found, check prototype (pIndexData->extra_descr)
        prototype = getattr(obj, "prototype", None)
        if prototype:
            for ed in getattr(prototype, "extra_descr", []):
                if ed.description:
                    lines.append(ed.description)
                    break

    return "\n".join(lines)


def _look_in(char: Character, args: str) -> str:
    """Look inside a container - ROM src/act_info.c lines 1070-1130"""
    from mud.world.obj_find import get_obj_here
    from mud.models.constants import ItemType

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
        # Show liquid amount
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
        return f"It's {amount}filled with a liquid."

    if item_type in (ItemType.CONTAINER, ItemType.CORPSE_NPC, ItemType.CORPSE_PC):
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        # Check if closed (value[1] has CONT_CLOSED flag)
        if len(value) > 1 and (value[1] & 1):  # CONT_CLOSED = 1
            return "It is closed."

        contents = getattr(obj, "contains", None) or getattr(obj, "contained_items", [])
        if not contents:
            short = getattr(obj, "short_descr", None) or "It"
            return f"{short} is empty."

        lines = [f"{getattr(obj, 'short_descr', 'It')} holds:"]
        for item in contents:
            item_name = getattr(item, "short_descr", None) or getattr(item, "name", "something")
            lines.append(f"  {item_name}")
        return "\n".join(lines)

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
