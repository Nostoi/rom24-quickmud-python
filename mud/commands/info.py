from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import LEVEL_HERO


ROM_NEWLINE = "\n\r"
_COLUMNS_PER_ROW = 6
_COLUMN_WIDTH = 12


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    return trust if trust > 0 else level


def _visible_command_names(
    char: Character,
    *,
    min_level: int = 0,
    max_level: int | None = LEVEL_HERO - 1,
) -> list[str]:
    from mud.commands.dispatcher import COMMANDS

    trust = _get_trust(char)
    names: list[str] = []
    for command in COMMANDS:
        if not command.show:
            continue
        level = command.min_trust
        if level < min_level:
            continue
        if level > trust:
            continue
        if max_level is not None and level > max_level:
            continue
        names.append(command.name)
    return names


def _chunk_commands(names: list[str]) -> list[str]:
    if not names:
        return []
    rows: list[str] = []
    current: list[str] = []
    for index, name in enumerate(names, start=1):
        current.append(f"{name:<{_COLUMN_WIDTH}}")
        if index % _COLUMNS_PER_ROW == 0:
            rows.append("".join(current).rstrip())
            current = []
    if current:
        rows.append("".join(current).rstrip())
    return rows


def do_commands(char: Character, args: str) -> str:
    """List mortal-accessible commands in ROM's six-column layout."""

    visible = _visible_command_names(char)
    rows = _chunk_commands(visible)
    if not rows:
        return ""
    return ROM_NEWLINE.join(rows) + ROM_NEWLINE


def do_wizhelp(char: Character, args: str) -> str:
    """List immortal commands available at or above hero level."""

    visible = _visible_command_names(char, min_level=LEVEL_HERO, max_level=None)
    rows = _chunk_commands(visible)
    if not rows:
        return ""
    return ROM_NEWLINE.join(rows) + ROM_NEWLINE


def do_who(char: Character, args: str) -> str:
    """
    List online players with filtering options.

    ROM Reference: src/act_info.c lines 2016-2226 (do_who)

    Usage:
        who                              - Show all players
        who 40 50                        - Show players level 40-50
        who warrior                      - Show only warriors
        who human                        - Show only humans
        who immortals                    - Show only immortals
        who 40 50 elf warrior            - Combine filters

    Shows all connected players with level, race, class, status flags, name, and title.
    """
    from mud.models.classes import CLASS_TABLE, get_player_class
    from mud.models.constants import (
        CommFlag,
        LEVEL_HERO,
        LEVEL_IMMORTAL,
        MAX_LEVEL,
        PlayerFlag,
    )
    from mud.models.races import get_race, PC_RACE_TABLE
    from mud.net.session import SESSIONS
    from mud.world.vision import can_see_character

    # Parse arguments (mirroring ROM C lines 2022-2128)
    level_lower = 0
    level_upper = MAX_LEVEL
    class_restrict: set[int] = set()
    race_restrict: set[int] = set()
    clan_restrict: set[int] = set()  # For future clan system
    immortals_only = False
    clan_only = False
    number_count = 0

    # Tokenize arguments
    tokens = args.split()
    for token in tokens:
        # Check if numeric (level range)
        if token.isdigit():
            number_count += 1
            if number_count == 1:
                level_lower = int(token)
            elif number_count == 2:
                level_upper = int(token)
            else:
                return "Only two level numbers allowed." + ROM_NEWLINE
        else:
            # Check for "immortals" keyword
            if token.lower().startswith("immortal"):
                immortals_only = True
            # Check for "clan" keyword
            elif token.lower() == "clan":
                clan_only = True
            else:
                # Try class lookup
                class_data = get_player_class(token)
                if class_data:
                    # Find class index
                    for idx, cls in enumerate(CLASS_TABLE):
                        if cls.name == class_data.name:
                            class_restrict.add(idx)
                            break
                else:
                    # Try race lookup
                    race_data = get_race(token)
                    if race_data:
                        # Find race index
                        for idx, race in enumerate(PC_RACE_TABLE):
                            if race.name == race_data.name:
                                race_restrict.add(idx)
                                break
                    else:
                        # Invalid argument
                        return f"That's not a valid race, class, or clan." + ROM_NEWLINE

    # Build player list (mirroring ROM C lines 2130-2219)
    lines = []
    match_count = 0

    for sess in SESSIONS.values():
        wch = sess.character
        if not wch:
            continue

        # Check visibility (ROM C line 2145-2151)
        if not can_see_character(char, wch):
            continue

        # Apply filters (ROM C lines 2153-2160)
        if wch.level < level_lower or wch.level > level_upper:
            continue
        if immortals_only and wch.level < LEVEL_IMMORTAL:
            continue
        if class_restrict and wch.ch_class not in class_restrict:
            continue
        if race_restrict and wch.race not in race_restrict:
            continue
        # clan_only and clan_restrict checks would go here (future clan system)

        match_count += 1

        # Determine class display (immortal rank or class name) (ROM C lines 2167-2201)
        class_name = CLASS_TABLE[wch.ch_class].who_name if wch.ch_class < len(CLASS_TABLE) else "???"
        if wch.level == MAX_LEVEL - 0:
            class_name = "IMP"
        elif wch.level == MAX_LEVEL - 1:
            class_name = "CRE"
        elif wch.level == MAX_LEVEL - 2:
            class_name = "SUP"
        elif wch.level == MAX_LEVEL - 3:
            class_name = "DEI"
        elif wch.level == MAX_LEVEL - 4:
            class_name = "GOD"
        elif wch.level == MAX_LEVEL - 5:
            class_name = "IMM"
        elif wch.level == MAX_LEVEL - 6:
            class_name = "DEM"
        elif wch.level == MAX_LEVEL - 7:
            class_name = "ANG"
        elif wch.level == MAX_LEVEL - 8:
            class_name = "AVA"

        # Get race WHO name (ROM C lines 2208-2209)
        race_who_name = "     "  # 5 spaces default
        if wch.race < len(PC_RACE_TABLE):
            race_who_name = PC_RACE_TABLE[wch.race].who_name

        # Build status flags (ROM C lines 2211-2216)
        flags = []
        if hasattr(wch, "incog_level") and wch.incog_level >= LEVEL_HERO:
            flags.append("(Incog)")
        if hasattr(wch, "invis_level") and wch.invis_level >= LEVEL_HERO:
            flags.append("(Wizi)")
        # Clan WHO name would go here (future clan system)
        if wch.comm & CommFlag.AFK:
            flags.append("[AFK]")
        if wch.act & PlayerFlag.KILLER:
            flags.append("(KILLER)")
        if wch.act & PlayerFlag.THIEF:
            flags.append("(THIEF)")

        # Format output line (ROM C lines 2206-2217)
        # Format: [Lv Race   Class] (Flags) Name Title
        flag_str = " ".join(flags)
        if flag_str:
            flag_str += " "

        title = getattr(wch, "title", "")
        lines.append(f"[{wch.level:2d} {race_who_name:6s} {class_name:3s}] {flag_str}{wch.name}{title}")

    # Footer (ROM C lines 2221-2222)
    lines.append("")
    lines.append(f"Players found: {match_count}")

    return ROM_NEWLINE.join(lines) + ROM_NEWLINE


def do_areas(char: Character, args: str) -> str:
    """
    List all areas in the game.

    ROM Reference: src/act_info.c lines 220-280 (do_areas)

    Usage: areas

    Shows all available areas with their level ranges and builders.
    """
    from mud.registry import area_registry

    lines = ["Area Name                             Recommended Levels"]
    lines.append("----------------------------------------------------")

    # Sort areas by min_vnum
    sorted_areas = sorted(area_registry.values(), key=lambda a: getattr(a, "min_vnum", 0))

    for area in sorted_areas:
        name = getattr(area, "name", "Unknown")
        low = getattr(area, "low_range", 0)
        high = getattr(area, "high_range", 0)

        # Format: "Area Name                             [ 1- 10]"
        lines.append(f"{name:38s} [{low:3d}-{high:3d}]")

    return ROM_NEWLINE.join(lines) + ROM_NEWLINE


def do_where(char: Character, args: str) -> str:
    """
    Show players/mobs in current area.

    ROM Reference: src/act_info.c lines 2407-2464 (do_where)

    Usage: where [target]

    Mode 1 (no args): Lists all players in the same area as you.
    Mode 2 (with args): Searches for specific character/mob in same area.

    Note: Both modes only search current area, not the entire world.
    """
    from mud.net.session import SESSIONS
    from mud.world.vision import can_see_character
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You are nowhere!"

    char_area = getattr(char_room, "area", None)
    if not char_area:
        return "You are in an unknown area."

    # ROM C Mode 1: no arguments (list all players in area)
    arg = args.strip()
    if not arg:
        lines = ["Players near you:"]
        found = False

        # ROM C iterates over descriptor_list (src/act_info.c line 2421)
        for sess in SESSIONS.values():
            victim = sess.character
            if not victim:
                continue

            # ROM C check: !IS_NPC (victim) - only show players, not NPCs
            if getattr(victim, "is_npc", True):
                continue

            victim_room = getattr(victim, "room", None)
            if not victim_room:
                continue

            # ROM C check: !IS_SET(victim->in_room->room_flags, ROOM_NOWHERE)
            room_flags = getattr(victim_room, "room_flags", 0)
            if room_flags & RoomFlag.ROOM_NOWHERE:
                continue

            # ROM C check: is_room_owner(ch, victim->in_room) || !room_is_private(victim->in_room)
            # TODO: Implement is_room_owner and room_is_private checks
            # For now, skip private room check (will be added in future)

            victim_area = getattr(victim_room, "area", None)
            if victim_area != char_area:
                continue

            # ROM C check: can_see(ch, victim)
            if not can_see_character(char, victim):
                continue

            # Format: "%-28s %s\n\r" (ROM C line 2433-2434)
            victim_name = getattr(victim, "name", "Unknown")
            victim_room_name = getattr(victim_room, "name", "somewhere")
            lines.append(f"{victim_name:28s} {victim_room_name}")
            found = True

        if not found:
            lines.append("None")

        return ROM_NEWLINE.join(lines) + ROM_NEWLINE

    # ROM C Mode 2: with argument (search for specific target)
    # ROM C Reference: src/act_info.c lines 2441-2461
    else:
        from mud.models.character import character_registry
        from mud.models.constants import AffectFlag
        from mud.world.char_find import is_name
        from mud.utils.act import _pers

        found = False

        # ROM C iterates char_list for all characters (NPCs + players)
        for victim in character_registry:
            victim_room = getattr(victim, "room", None)
            if not victim_room:
                continue

            # ROM C check: victim->in_room->area == ch->in_room->area
            victim_area = getattr(victim_room, "area", None)
            if victim_area != char_area:
                continue

            # ROM C check: !IS_AFFECTED(victim, AFF_HIDE)
            victim_affected_by = getattr(victim, "affected_by", 0)
            if victim_affected_by & AffectFlag.HIDE:
                continue

            # ROM C check: !IS_AFFECTED(victim, AFF_SNEAK)
            if victim_affected_by & AffectFlag.SNEAK:
                continue

            # ROM C check: can_see(ch, victim)
            if not can_see_character(char, victim):
                continue

            # ROM C check: is_name(arg, victim->name)
            victim_name = getattr(victim, "name", "")
            if not is_name(arg, victim_name):
                continue

            # Found match! Format and return
            found = True
            # ROM C uses PERS(victim, ch) for display name
            display_name = _pers(victim, char)
            victim_room_name = getattr(victim_room, "name", "somewhere")
            # Format: "%-28s %s\n\r" (ROM C line 2453-2454)
            result = f"{display_name:28s} {victim_room_name}" + ROM_NEWLINE
            return result  # ROM C breaks after first match (line 2456)

        # ROM C: if not found, act("You didn't find any $T.", ...)
        if not found:
            from mud.utils.act import act_format

            return act_format("You didn't find any $T.", recipient=char, actor=char, arg1=None, arg2=arg) + ROM_NEWLINE


def do_time(char: Character, args: str) -> str:
    """
    Display game time.

    ROM Reference: src/act_info.c lines 2350-2400 (do_time)

    Usage: time

    Shows the current game time and date.
    """
    from mud.time import time_info

    # ROM month names
    month_names = [
        "Winter",
        "the Winter Wolf",
        "the Frost Giant",
        "the Old Forces",
        "the Grand Struggle",
        "the Spring",
        "Nature",
        "Futility",
        "the Dragon",
        "the Sun",
        "the Heat",
        "the Battle",
        "the Dark Shades",
        "the Shadows",
        "the Long Shadows",
        "the Ancient Darkness",
        "the Great Evil",
    ]

    # Get time info
    hour = time_info.hour
    day = time_info.day + 1  # ROM days are 1-based for display (ROM C line 1778)
    month = time_info.month
    year = time_info.year

    # ROM C ordinal suffix logic (src/act_info.c lines 1780-1789)
    # Note: day already has +1 applied (line 1778: day = time_info.day + 1)
    if 5 <= day <= 19:
        day_suffix = "th"
    elif day % 10 == 1:
        day_suffix = "st"
    elif day % 10 == 2:
        day_suffix = "nd"
    elif day % 10 == 3:
        day_suffix = "rd"
    else:
        day_suffix = "th"

    # ROM C 12-hour conversion (line 1793): (hour % 12 == 0) ? 12 : hour % 12
    hour_12 = 12 if (hour % 12 == 0) else hour % 12
    am_pm = "pm" if hour >= 12 else "am"

    month_name = month_names[month] if 0 <= month < len(month_names) else "Unknown"

    # ROM C: day_name[day % 7] where day = time_info.day + 1 (lines 1778, 1795)
    # ROM C day_name array has "the" prefix (line 1759-1762)
    day_names = ["the Moon", "the Bull", "Deception", "Thunder", "Freedom", "the Great Gods", "the Sun"]
    day_name = day_names[day % 7]

    # ROM C format (line 1791-1795): "It is %d o'clock %s, Day of %s, %d%s the Month of %s.\n\r"
    result = f"It is {hour_12} o'clock {am_pm}, Day of {day_name}, {day}{day_suffix} the Month of {month_name}.\n\r"

    # ROM C lines 1797-1798: Boot time and system time display
    # sprintf(buf, "ROM started up at %s\n\rThe system time is %s.\n\r", str_boot_time, (char *) ctime(&current_time));
    from datetime import datetime
    import mud.game_loop

    # Get boot time (stored at server startup)
    boot_time_obj = getattr(mud.game_loop, "boot_time", None)
    if boot_time_obj:
        # Format like ROM C ctime(): "Wed Jun 30 21:49:08 1993"
        # Use %-d to avoid zero-padding for single-digit days (matching ctime)
        boot_str = boot_time_obj.strftime("%a %b %-d %H:%M:%S %Y")
        result += f"ROM started up at {boot_str}\n\r"

    # Get current system time
    current_time = datetime.now()
    time_str = current_time.strftime("%a %b %-d %H:%M:%S %Y")
    result += f"The system time is {time_str}.\n\r"

    return result


def do_weather(char: Character, args: str) -> str:
    """
    Display weather conditions.

    ROM Reference: src/act_info.c lines 1806-1830 (do_weather)

    Usage: weather

    Shows current weather (sky and wind direction).
    """
    from mud.game_loop import weather, SkyState
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You can't see the sky from nowhere.\n\r"

    # ROM C: IS_OUTSIDE(ch) checks ROOM_INDOORS flag (merc.h:2112-2114)
    room_flags = getattr(char_room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_INDOORS:
        return "You can't see the weather indoors.\n\r"

    # ROM C sky descriptions (src/act_info.c lines 1810-1815)
    sky_look = [
        "cloudless",  # SkyState.CLOUDLESS (0)
        "cloudy",  # SkyState.CLOUDY (1)
        "rainy",  # SkyState.RAINING (2)
        "lit by flashes of lightning",  # SkyState.LIGHTNING (3)
    ]

    # Get sky description with bounds checking
    sky_desc = sky_look[weather.sky] if 0 <= weather.sky < len(sky_look) else "strange"

    # ROM C wind direction logic (src/act_info.c lines 1826-1828)
    # weather.change >= 0: pressure rising/stable (warm south wind)
    # weather.change < 0:  pressure falling (cold north wind)
    wind = "a warm southerly breeze blows" if weather.change >= 0 else "a cold northern gust blows"

    # ROM C output format: "The sky is {sky} and {wind}."
    return f"The sky is {sky_desc} and {wind}.\n\r"


def do_credits(char: Character, args: str) -> str:
    """
    Display ROM credits.

    ROM Reference: src/act_info.c lines 150-200 (do_credits)

    Usage: credits

    Shows credits for ROM MUD and its predecessors.
    """
    lines = [
        "QuickMUD - A Python port of ROM 2.4b6",
        "",
        "ROM 2.4 is copyright 1993-1998 Russ Taylor",
        "ROM has been brought to you by the ROM consortium:",
        "    Russ Taylor (rtaylor@hypercube.org)",
        "    Gabrielle Taylor (gtaylor@hypercube.org)",
        "    Brian Moore (zump@rom.org)",
        "",
        "By using this mud you agree to abide by the ROM and DikuMUD licenses.",
        "Type 'help ROM' or 'help DIKU' for more information.",
        "",
        "Thanks to all who have contributed to the ROM community over the years!",
    ]
    return ROM_NEWLINE.join(lines) + ROM_NEWLINE


def do_report(char: Character, args: str) -> str:
    """
    Report your status to the room.

    ROM Reference: src/act_info.c lines 2658-2676 (do_report)

    Usage: report

    Reports your hit points, mana, movement, and experience to the room.
    """
    # Get character stats
    # ROM C: ch->hit, ch->max_hit, ch->mana, ch->max_mana, ch->move, ch->max_move, ch->exp
    hit = getattr(char, "hit", 0)
    max_hit = getattr(char, "max_hit", 1)
    mana = getattr(char, "mana", 0)
    max_mana = getattr(char, "max_mana", 1)
    move = getattr(char, "move", 0)
    max_move = getattr(char, "max_move", 1)
    exp = getattr(char, "exp", 0)

    # ROM C format: "You say 'I have %d/%d hp %d/%d mana %d/%d mv %d xp.'"
    msg_to_self = f"You say 'I have {hit}/{max_hit} hp {mana}/{max_mana} mana {move}/{max_move} mv {exp} xp.'"

    # Broadcast to room
    # ROM C format: "$n says 'I have %d/%d hp %d/%d mana %d/%d mv %d xp.'"
    room = getattr(char, "room", None)
    if room:
        char_name = getattr(char, "name", "Someone")
        room_msg = f"{char_name} says 'I have {hit}/{max_hit} hp {mana}/{max_mana} mana {move}/{max_move} mv {exp} xp.'"

        # Send to all other characters in room
        for other in getattr(room, "people", []):
            if other != char:
                try:
                    desc = getattr(other, "desc", None)
                    if desc and hasattr(desc, "send"):
                        desc.send(room_msg)
                except Exception:
                    pass

    return msg_to_self
