"""
Information commands - examine, read, count, whois, worth, sit.

ROM Reference: src/act_info.c do_examine, do_read, do_count, do_whois, do_worth
ROM Reference: src/act_move.c do_sit
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ItemType


def do_examine(char: Character, args: str) -> str:
    """
    Examine an object - look + show contents.

    ROM Reference: src/act_info.c do_examine (lines 1320-1385)

    Does a look, then shows additional info for containers, money, etc.
    """
    if not args or not args.strip():
        return "Examine what?"

    target = args.strip().split()[0]

    # First, do a look
    from mud.commands.inspection import do_look

    result = do_look(char, target)

    # Find the object to show additional info
    from mud.world.obj_find import get_obj_here

    obj = get_obj_here(char, target)

    if obj is None:
        return result

    # Get item type
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            item_type = getattr(proto, "item_type", None)

    # Additional info based on item type
    extra_info = ""

    # Handle jukebox - show song list
    if item_type == ItemType.JUKEBOX or str(item_type) == "jukebox":
        from mud.commands.player_info import do_play

        extra_info = "\n" + do_play(char, "list")

    elif item_type == ItemType.MONEY or str(item_type) == "money":
        # Show coin count
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        silver = value[0] if len(value) > 0 else 0
        gold = value[1] if len(value) > 1 else 0

        if silver == 0 and gold == 0:
            extra_info = "\nOdd...there's no coins in the pile."
        elif silver == 0:
            if gold == 1:
                extra_info = "\nWow. One gold coin."
            else:
                extra_info = f"\nThere are {gold} gold coins in the pile."
        elif gold == 0:
            if silver == 1:
                extra_info = "\nWow. One silver coin."
            else:
                extra_info = f"\nThere are {silver} silver coins in the pile."
        else:
            extra_info = f"\nThere are {gold} gold and {silver} silver coins in the pile."

    elif item_type in (
        ItemType.CONTAINER,
        ItemType.CORPSE_NPC,
        ItemType.CORPSE_PC,
        "container",
        "corpse_npc",
        "corpse_pc",
    ):
        # Show contents (ROM C line 1380: uses original argument, not split arg)
        from mud.commands.inspection import do_look

        extra_info = "\n" + do_look(char, f"in {args}")

    elif item_type == ItemType.DRINK_CON or str(item_type) == "drink_con":
        # Show liquid info (ROM C line 1380: uses original argument)
        from mud.commands.inspection import do_look

        extra_info = "\n" + do_look(char, f"in {args}")

    return result + extra_info


def do_read(char: Character, args: str) -> str:
    """
    Read something - alias for look.

    ROM Reference: src/act_info.c do_read (lines 1315-1318)

    Just calls do_look.
    """
    from mud.commands.inspection import do_look

    return do_look(char, args)


def do_count(char: Character, args: str) -> str:
    """
    Count players currently online.

    ROM Reference: src/act_info.c do_count (lines 2228-2252)
    """
    from mud import registry

    count = 0
    for desc in getattr(registry, "descriptor_list", []):
        if hasattr(desc, "character") and desc.character:
            count += 1

    # Check player registry as fallback
    if count == 0:
        players = getattr(registry, "player_registry", {})
        count = len(players)

    # Track max online
    max_on = getattr(registry, "max_on_today", 0)
    if count > max_on:
        registry.max_on_today = count
        max_on = count

    if max_on == count:
        return f"There are {count} characters on, the most so far today."
    else:
        return f"There are {count} characters on, the most on today was {max_on}."


def do_whois(char: Character, args: str) -> str:
    """
    Get information about a specific player.

    ROM Reference: src/act_info.c do_whois (lines 1916-2010)
    """
    from mud.models.clans import CLAN_TABLE
    from mud.models.classes import CLASS_TABLE
    from mud.models.constants import LEVEL_HERO, MAX_LEVEL, CommFlag, PlayerFlag
    from mud.models.races import PC_RACE_TABLE
    from mud.net.connection import CON_PLAYING
    from mud.world.vision import can_see_character

    if not args or not args.strip():
        return "You must provide a name."

    target_name = args.strip().split()[0].lower()

    from mud import registry

    def class_display_for(wch: Character) -> str:
        level = getattr(wch, "level", 1)
        if level == MAX_LEVEL - 0:
            return "IMP"
        if level == MAX_LEVEL - 1:
            return "CRE"
        if level == MAX_LEVEL - 2:
            return "SUP"
        if level == MAX_LEVEL - 3:
            return "DEI"
        if level == MAX_LEVEL - 4:
            return "GOD"
        if level == MAX_LEVEL - 5:
            return "IMM"
        if level == MAX_LEVEL - 6:
            return "DEM"
        if level == MAX_LEVEL - 7:
            return "ANG"
        if level == MAX_LEVEL - 8:
            return "AVA"
        ch_class = getattr(wch, "ch_class", 0)
        if 0 <= ch_class < len(CLASS_TABLE):
            return CLASS_TABLE[ch_class].who_name
        return "???"

    def race_who_name_for(wch: Character) -> str:
        race = getattr(wch, "race", 0)
        if isinstance(race, int) and 0 <= race < len(PC_RACE_TABLE):
            return PC_RACE_TABLE[race].who_name
        return "     "

    def clan_who_name_for(wch: Character) -> str:
        clan = getattr(wch, "clan", 0)
        if isinstance(clan, int) and 0 <= clan < len(CLAN_TABLE):
            return CLAN_TABLE[clan].who_name
        return ""

    def format_whois_line(wch: Character) -> str:
        level = getattr(wch, "level", 1)
        race_who_name = race_who_name_for(wch)
        class_display = class_display_for(wch)
        flags: list[str] = []
        if getattr(wch, "incog_level", 0) >= LEVEL_HERO:
            flags.append("(Incog)")
        if getattr(wch, "invis_level", 0) >= LEVEL_HERO:
            flags.append("(Wizi)")

        clan_who_name = clan_who_name_for(wch)
        if clan_who_name:
            flags.append(clan_who_name.rstrip())
        if getattr(wch, "comm", 0) & CommFlag.AFK:
            flags.append("[AFK]")
        if getattr(wch, "act", 0) & PlayerFlag.KILLER:
            flags.append("(KILLER)")
        if getattr(wch, "act", 0) & PlayerFlag.THIEF:
            flags.append("(THIEF)")

        flag_str = ""
        if flags:
            flag_str = " ".join(flags) + " "

        name = getattr(wch, "name", "Unknown")
        title = ""
        if not getattr(wch, "is_npc", False):
            pcdata = getattr(wch, "pcdata", None)
            title = getattr(pcdata, "title", "") if pcdata is not None else getattr(wch, "title", "")

        return f"[{level:2d} {race_who_name:6s} {class_display:3s}] {flag_str}{name}{title}"

    results = []

    # Search descriptor list first, mirroring ROM src/act_info.c:1933-2008
    for desc in getattr(registry, "descriptor_list", []):
        if getattr(desc, "connected", 0) != CON_PLAYING:
            continue
        if not hasattr(desc, "character") or not desc.character:
            continue
        if not can_see_character(char, desc.character):
            continue

        wch = desc.original if getattr(desc, "original", None) is not None else desc.character
        if not can_see_character(char, wch):
            continue

        wch_name = (getattr(wch, "name", None) or "").lower()

        if wch_name.startswith(target_name):
            results.append(format_whois_line(wch))

    # Fallback for tests/contexts without descriptor-backed sessions.
    players = getattr(registry, "player_registry", {})
    for name, player in players.items():
        if name.lower().startswith(target_name):
            if any(name.lower() in r.lower() for r in results):
                continue  # Already in list
            results.append(format_whois_line(player))

    if not results:
        return "No one of that name is playing."

    return "\n".join(results)


def do_worth(char: Character, args: str) -> str:
    """
    Show character's monetary worth and experience.

    ROM Reference: src/act_info.c do_worth (lines 1453-1472)
    """
    gold = getattr(char, "gold", 0)
    silver = getattr(char, "silver", 0)

    is_npc = getattr(char, "is_npc", False)

    if is_npc:
        return f"You have {gold} gold and {silver} silver."

    exp = getattr(char, "exp", 0)
    level = getattr(char, "level", 1)

    # Calculate exp to next level
    exp_per_lvl = _exp_per_level(char)
    exp_to_level = (level + 1) * exp_per_lvl - exp

    return f"You have {gold} gold, {silver} silver, and {exp} experience ({exp_to_level} exp to level)."


def _exp_per_level(char: Character) -> int:
    """
    Calculate experience per level using ROM C formula.

    ROM Reference: src/skills.c exp_per_level (lines 639-672)

    Returns base experience required per level, modified by creation points
    and race/class multipliers using ROM C's complex escalating formula.
    """
    from mud.models.races import PC_RACE_TABLE

    is_npc = getattr(char, "is_npc", False)
    if is_npc:
        return 1000

    pcdata = getattr(char, "pcdata", None)
    if not pcdata:
        return 1000

    points = getattr(pcdata, "points", 40)
    race_idx = getattr(char, "race", 0)
    class_idx = getattr(char, "ch_class", 0)

    class_mult = 100
    if 0 <= race_idx < len(PC_RACE_TABLE):
        race = PC_RACE_TABLE[race_idx]
        if hasattr(race, "class_multipliers"):
            class_multipliers = race.class_multipliers
            if 0 <= class_idx < len(class_multipliers):
                class_mult = class_multipliers[class_idx]

    if points < 40:
        return 1000 * (class_mult // 100 if class_mult else 1)

    expl = 1000
    inc = 500
    points -= 40

    while points > 9:
        expl += inc
        points -= 10
        if points > 9:
            expl += inc
            inc *= 2
            points -= 10

    expl += points * inc // 10

    return expl * class_mult // 100
