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
    List online players.

    ROM Reference: src/act_info.c lines 2016-2250 (do_who)

    Usage: who [filters]

    Shows all connected players with name, title, level, and class.
    Filters can include level ranges, class names, or race names.
    """
    from mud.net.session import SESSIONS

    # For basic implementation, just show all players
    # ROM version has complex filtering by class/race/clan/level
    lines = ["Players"]
    lines.append("-------")

    player_count = 0
    for sess in SESSIONS.values():
        ch = sess.character
        if not ch:
            continue

        # Get player info
        name = getattr(ch, "name", "Unknown")
        level = getattr(ch, "level", 1)
        title = getattr(ch, "title", "")

        # Format player line (simplified ROM format)
        if title:
            lines.append(f"[{level:2d}] {name} {title}")
        else:
            lines.append(f"[{level:2d}] {name}")
        player_count += 1

    lines.append("")
    lines.append(f"Players found: {player_count}")
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
    Show players in current area.

    ROM Reference: src/act_info.c lines 2200-2280 (do_where)

    Usage: where

    Lists all players in the same area as you.
    """
    from mud.net.session import SESSIONS

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You are nowhere!"

    char_area_vnum = getattr(getattr(char_room, "area", None), "vnum", None)
    if char_area_vnum is None:
        return "You are in an unknown area."

    lines = [f"Players near you in {getattr(getattr(char_room, 'area', None), 'name', 'this area')}:"]

    found = False
    for sess in SESSIONS.values():
        ch = sess.character
        if not ch:
            continue

        room = getattr(ch, "room", None)
        if not room:
            continue

        area = getattr(room, "area", None)
        area_vnum = getattr(area, "vnum", None)

        if area_vnum == char_area_vnum:
            name = getattr(ch, "name", "Unknown")
            room_name = getattr(room, "name", "somewhere")
            lines.append(f"  {name:28s} {room_name}")
            found = True

    if not found:
        lines.append("  None")

    return ROM_NEWLINE.join(lines) + ROM_NEWLINE


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
    day = time_info.day + 1  # ROM days are 1-based for display
    month = time_info.month
    year = time_info.year

    # Convert hour to 12-hour format
    if hour == 0:
        time_str = "12 AM"
    elif hour < 12:
        time_str = f"{hour} AM"
    elif hour == 12:
        time_str = "12 PM"
    else:
        time_str = f"{hour - 12} PM"

    month_name = month_names[month] if 0 <= month < len(month_names) else "Unknown"

    return f"It is {time_str}, Day of the {['Moon', 'Bull', 'Deception', 'Thunder', 'Freedom', 'Great Gods', 'Sun'][day % 7]}, {day}{['th', 'st', 'nd', 'rd', 'th'][min(day % 10, 4)]} the Month of {month_name}, {year} A.D."


def do_weather(char: Character, args: str) -> str:
    """
    Display weather conditions.

    ROM Reference: src/act_info.c lines 2420-2480 (do_weather)

    Usage: weather

    Shows current weather and sky conditions.
    """
    from mud.game_loop import weather, SkyState
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You can't see the sky from nowhere."

    # Check if in a room where you can see the sky
    # ROM Reference: src/act_info.c checks room_flags & ROOM_INDOORS
    room_flags = getattr(char_room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_INDOORS:
        return "You can't see the sky from here."

    # Get weather conditions
    sky_msgs = {
        SkyState.CLOUDLESS: "The sky is cloudless.",
        SkyState.CLOUDY: "The sky is cloudy.",
        SkyState.RAINING: "It is raining.",
        SkyState.LIGHTNING: "Lightning flashes in the sky.",
    }

    msg = sky_msgs.get(weather.sky, "The sky is strange.")
    return msg


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

    ROM Reference: src/act_comm.c lines 800-850 (do_report)

    Usage: report

    Reports your hit points, mana, and movement to everyone in the room.
    """
    # Get character stats - ROM uses hit/max_hit, not hp/max_hp
    # ROM Reference: src/act_comm.c:800-850 uses ch->hit, ch->max_hit
    hit = getattr(char, "hit", 0)
    max_hit = getattr(char, "max_hit", 1)
    mana = getattr(char, "mana", 0)
    max_mana = getattr(char, "max_mana", 1)
    move = getattr(char, "move", 0)
    max_move = getattr(char, "max_move", 1)

    # Calculate percentages
    hp_pct = (hit * 100) // max_hit if max_hit > 0 else 0
    mana_pct = (mana * 100) // max_mana if max_mana > 0 else 0
    move_pct = (move * 100) // max_move if max_move > 0 else 0

    # Message to self
    msg = f"You report: {hit}/{max_hit} hp {mana}/{max_mana} mana {move}/{max_move} mv."

    # Broadcast to room
    room = getattr(char, "room", None)
    if room:
        char_name = getattr(char, "name", "Someone")
        room_msg = f"{char_name} reports: {hp_pct}% hp {mana_pct}% mana {move_pct}% mv."

        for other in getattr(room, "characters", []):
            if other != char:
                try:
                    desc = getattr(other, "desc", None)
                    if desc and hasattr(desc, "send"):
                        desc.send(room_msg)
                except Exception:
                    pass

    return msg
