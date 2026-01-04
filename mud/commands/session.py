"""
Session and character information commands.

Implements save, quit, score, and recall commands for ROM parity.
ROM References: src/act_comm.c (save/quit), src/act_info.c (score), src/act_move.c (recall)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import Position

if TYPE_CHECKING:
    from mud.models.character import Character


def do_save(ch: Character, args: str) -> str:
    """
    Save character to database.

    ROM Reference: src/act_comm.c lines 1533-1555 (do_save)
    """
    from mud.account.account_manager import save_character

    if getattr(ch, "is_npc", False):
        return "NPCs cannot save."

    try:
        save_character(ch)
        return "Saving. Remember that ROM has automatic saving now."
    except Exception as e:
        return f"Save failed: {e}"


def do_quit(ch: Character, args: str) -> str:
    """
    Quit the game.

    ROM Reference: src/act_comm.c lines 1496-1531 (do_quit)
    """
    from mud.account.account_manager import save_character

    if ch.position == Position.FIGHTING:
        return "No way! You are fighting."

    if ch.position < Position.STUNNED:
        return "You're not DEAD yet."

    if not getattr(ch, "is_npc", False):
        try:
            save_character(ch)
        except Exception as exc:
            print(f"[ERROR] Failed to save character on quit: {exc}")

    # Set a flag to signal the connection handler to disconnect
    setattr(ch, "_quit_requested", True)

    return "May your travels be safe.\n"


def do_score(ch: Character, args: str) -> str:
    """
    Display character statistics.

    ROM Reference: src/act_info.c lines 580-732 (do_score)
    """
    # Build score output mirroring ROM format
    lines = []

    # Name and title - ROM src/act_info.c lines 1482-1488
    name = getattr(ch, "name", "Unknown")
    title = getattr(ch, "title", "")
    level = getattr(ch, "level", 1)

    # Get age and played hours
    from mud.handler import get_age
    import time

    age = get_age(ch)
    played = getattr(ch, "played", 0)
    logon = getattr(ch, "logon", time.time())
    current_time = time.time()
    total_hours = (played + int(current_time - logon)) // 3600

    if title:
        lines.append(f"You are {name}{title}, level {level}, {age} years old ({total_hours} hours).")
    else:
        lines.append(f"You are {name}, level {level}, {age} years old ({total_hours} hours).")

    # Trust level - ROM src/act_info.c lines 1490-1494
    from mud.commands.imm_commands import get_trust

    trust = get_trust(ch)
    if trust != level:
        lines.append(f"You are trusted at level {trust}.")

    # Race, sex, class - ROM src/act_info.c lines 1496-1500
    race = getattr(ch, "race", "unknown")
    sex = getattr(ch, "sex", 0)
    sex_name = "sexless" if sex == 0 else ("male" if sex == 1 else "female")
    class_name = getattr(ch, "class_name", "unknown")
    lines.append(f"Race: {race}  Sex: {sex_name}  Class: {class_name}")

    # HP, Mana, Movement
    hp = getattr(ch, "hit", 0)
    max_hp = getattr(ch, "max_hit", 0)
    mana = getattr(ch, "mana", 0)
    max_mana = getattr(ch, "max_mana", 0)
    move = getattr(ch, "move", 0)
    max_move = getattr(ch, "max_move", 0)

    lines.append(f"You have {hp}/{max_hp} hit, {mana}/{max_mana} mana, {move}/{max_move} movement.")

    # Practice and training sessions - ROM src/act_info.c lines 1509-1512
    if not getattr(ch, "is_npc", False):
        practice = getattr(ch, "practice", 0)
        train = getattr(ch, "train", 0)
        lines.append(f"You have {practice} practices and {train} training sessions.")

    # Stats - mirroring ROM perm_stat[STAT_STR] through perm_stat[STAT_CON]
    # ROM defines: STAT_STR=0, STAT_INT=1, STAT_WIS=2, STAT_DEX=3, STAT_CON=4
    # ROM src/act_info.c lines 1520-1531 - shows both perm and current stats
    perm_stat = getattr(ch, "perm_stat", [13, 13, 13, 13, 13])
    perm_str = perm_stat[0] if len(perm_stat) > 0 else 13
    perm_int = perm_stat[1] if len(perm_stat) > 1 else 13
    perm_wis = perm_stat[2] if len(perm_stat) > 2 else 13
    perm_dex = perm_stat[3] if len(perm_stat) > 3 else 13
    perm_con = perm_stat[4] if len(perm_stat) > 4 else 13

    # Get current (buffed) stats using get_curr_stat
    curr_str = ch.get_curr_stat(0) if hasattr(ch, "get_curr_stat") else perm_str
    curr_int = ch.get_curr_stat(1) if hasattr(ch, "get_curr_stat") else perm_int
    curr_wis = ch.get_curr_stat(2) if hasattr(ch, "get_curr_stat") else perm_wis
    curr_dex = ch.get_curr_stat(3) if hasattr(ch, "get_curr_stat") else perm_dex
    curr_con = ch.get_curr_stat(4) if hasattr(ch, "get_curr_stat") else perm_con

    # Display format: "Str: perm(current)" - matches ROM C format
    lines.append(
        f"Str: {perm_str}({curr_str})  "
        f"Int: {perm_int}({curr_int})  "
        f"Wis: {perm_wis}({curr_wis})  "
        f"Dex: {perm_dex}({curr_dex})  "
        f"Con: {perm_con}({curr_con})"
    )

    # Experience and gold - ROM src/act_info.c lines 1533-1536
    exp = getattr(ch, "exp", 0)
    gold = getattr(ch, "gold", 0)
    silver = getattr(ch, "silver", 0)
    lines.append(f"You have scored {exp} exp, and have {gold} gold and {silver} silver coins.")

    # Experience to level - ROM src/act_info.c lines 1538-1546
    if not getattr(ch, "is_npc", False) and level < 51:  # LEVEL_HERO = 51
        from mud.advancement import exp_per_level

        exp_needed = ((level + 1) * exp_per_level(ch)) - exp
        lines.append(f"You need {exp_needed} exp to level.")

    # Armor class - ROM displays individual ACs at level 25+ (src/act_info.c:1591-1650)
    # armor is list[AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC] where indices 0-3
    armor = getattr(ch, "armor", [100, 100, 100, 100])
    # Ensure armor is a list (sometimes can be int)
    if not isinstance(armor, list):
        armor = [armor, armor, armor, armor]

    if level >= 25:
        # High level: show all four armor types
        ac_pierce = armor[0] if len(armor) > 0 else 100
        ac_bash = armor[1] if len(armor) > 1 else 100
        ac_slash = armor[2] if len(armor) > 2 else 100
        ac_magic = armor[3] if len(armor) > 3 else 100
        lines.append(f"Armor: pierce: {ac_pierce}  bash: {ac_bash}  slash: {ac_slash}  magic: {ac_magic}")
    else:
        # Low level: show generic description based on AC_SLASH (index 2)
        ac_slash = armor[2] if len(armor) > 2 else 100
        lines.append(f"You are {_armor_class_description(ac_slash)} armored.")

    # Immortal info - ROM src/act_info.c lines 1654-1675
    from mud.models.constants import LEVEL_IMMORTAL, PlayerFlag

    if level >= LEVEL_IMMORTAL:
        imm_parts = []

        # Holy light status
        act_flags = getattr(ch, "act", 0)
        if act_flags & PlayerFlag.HOLYLIGHT:
            imm_parts.append("Holy Light: on")
        else:
            imm_parts.append("Holy Light: off")

        # Invisible level
        invis_level = getattr(ch, "invis_level", 0)
        if invis_level:
            imm_parts.append(f"Invisible: level {invis_level}")

        # Incognito level
        incog_level = getattr(ch, "incog_level", 0)
        if incog_level:
            imm_parts.append(f"Incognito: level {incog_level}")

        if imm_parts:
            lines.append("  ".join(imm_parts))

    # Hitroll and damroll - ROM src/act_info.c lines 1677-1682
    # Only display at level 15+
    if level >= 15:
        hitroll = getattr(ch, "hitroll", 0)
        damroll = getattr(ch, "damroll", 0)
        lines.append(f"Hitroll: {hitroll}  Damroll: {damroll}")

    # Alignment - ROM src/act_info.c lines 1684-1708
    alignment = getattr(ch, "alignment", 0)
    if level >= 10:
        # Show numeric alignment at level 10+
        alignment_desc = _get_alignment_description(alignment)
        lines.append(f"Alignment: {alignment}.  You are {alignment_desc}")
    else:
        # Show only description for low level
        alignment_desc = _get_alignment_description(alignment)
        lines.append(f"You are {alignment_desc}")

    # Position
    position = ch.position
    try:
        pos_enum = Position(position)
        lines.append(f"You are {pos_enum.name.lower()}.")
    except ValueError:
        lines.append(f"You are standing.")

    # Carrying - ROM src/act_info.c lines 1514-1518
    carry_weight = getattr(ch, "carry_weight", 0)
    carry_number = getattr(ch, "carry_number", 0)

    # Get max carrying capacity
    from mud.world.movement import can_carry_n, can_carry_w

    max_carry_number = can_carry_n(ch)
    max_carry_weight = can_carry_w(ch) // 10  # ROM divides by 10 for display

    lines.append(
        f"You are carrying {carry_number}/{max_carry_number} items "
        f"with weight {carry_weight // 10}/{max_carry_weight} pounds."
    )

    # Wimpy - ROM src/act_info.c lines 1548-1549
    wimpy = getattr(ch, "wimpy", 0)
    if wimpy > 0:
        lines.append(f"Wimpy set to {wimpy} hit points.")

    # Conditions - ROM src/act_info.c lines 1551-1556
    if not getattr(ch, "is_npc", False):
        # COND_DRUNK = 0, COND_FULL = 1, COND_THIRST = 2, COND_HUNGER = 3
        condition = getattr(ch, "condition", [0, 48, 48, 48])
        if len(condition) > 0 and condition[0] > 10:  # COND_DRUNK
            lines.append("You are drunk.")
        if len(condition) > 2 and condition[2] == 0:  # COND_THIRST
            lines.append("You are thirsty.")
        if len(condition) > 3 and condition[3] == 0:  # COND_HUNGER
            lines.append("You are hungry.")

    result = "\n".join(lines)

    # COMM_SHOW_AFFECTS integration - ROM src/act_info.c lines 1710-1711
    from mud.models.constants import CommFlag

    comm_flags = getattr(ch, "comm", 0)
    if comm_flags & CommFlag.SHOW_AFFECTS:
        # Auto-call do_affects if COMM_SHOW_AFFECTS is set
        from mud.commands.affects import do_affects

        result += "\n\n" + do_affects(ch, "")

    return result


def _armor_class_description(ac: int) -> str:
    """Convert armor class to ROM description."""
    if ac >= 101:
        return "hopelessly"
    elif ac >= 80:
        return "defenseless"
    elif ac >= 60:
        return "barely"
    elif ac >= 40:
        return "poorly"
    elif ac >= 20:
        return "somewhat"
    elif ac >= 0:
        return "well"
    elif ac >= -20:
        return "very well"
    elif ac >= -40:
        return "extremely well"
    elif ac >= -60:
        return "superbly"
    elif ac >= -80:
        return "almost invulnerably"
    else:
        return "divinely"


def _get_alignment_description(alignment: int) -> str:
    """
    Convert numeric alignment to ROM description.

    ROM Reference: src/act_info.c lines 1690-1708
    """
    if alignment > 900:
        return "angelic."
    elif alignment > 700:
        return "saintly."
    elif alignment > 350:
        return "good."
    elif alignment > 100:
        return "kind."
    elif alignment > -100:
        return "neutral."
    elif alignment > -350:
        return "mean."
    elif alignment > -700:
        return "evil."
    elif alignment > -900:
        return "demonic."
    else:
        return "satanic."


def do_recall(ch: Character, args: str) -> str:
    """
    Recall to temple (safe room).

    ROM Reference: src/act_move.c lines 1234-1299 (do_recall)
    """
    # Can't recall while fighting
    if ch.position == Position.FIGHTING:
        return "You can't recall while fighting!"

    # Can't recall if stunned or worse
    if ch.position < Position.STUNNED:
        return "You are hurt too badly to do that."

    # Get recall room (typically vnum 3001 - Temple of Mota)
    recall_vnum = 3001

    try:
        # Get world instance - use room_registry
        from mud.registry import room_registry

        # Find recall room
        recall_room = room_registry.get(recall_vnum)
        if not recall_room:
            return "You cannot recall from here."

        # Check if already in recall room
        if ch.room == recall_room:
            return "You are already in the temple!"

        # Move cost (10% of max movement)
        max_move = getattr(ch, "max_move", 100)
        cost = max(1, max_move // 10)

        if ch.move < cost:
            return "You don't have enough movement points."

        # Pay movement cost
        ch.move -= cost

        # Send messages
        old_room = ch.room
        result_messages = []

        # Message to old room
        if old_room:
            for other in old_room.characters:
                if other != ch:
                    try:
                        desc = getattr(other, "desc", None)
                        if desc and hasattr(desc, "send"):
                            desc.send(f"{ch.name} prays for transportation!")
                    except Exception:
                        pass

        # Move character
        if old_room and old_room in getattr(ch, "room", None).__class__.__mro__:
            old_room.characters.remove(ch)

        ch.room = recall_room
        recall_room.characters.append(ch)

        # Message to character
        result_messages.append("You pray for transportation!")

        # Message to new room
        for other in recall_room.characters:
            if other != ch:
                try:
                    desc = getattr(other, "desc", None)
                    if desc and hasattr(desc, "send"):
                        desc.send(f"{ch.name} appears in the room!")
                except Exception:
                    pass

        # Show room to character
        from mud.commands.inspection import do_look

        room_desc = do_look(ch, "")
        result_messages.append(room_desc)

        return "\n".join(result_messages)

    except Exception as e:
        return f"Recall failed: {e}"
