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
    # NPCs don't save
    if getattr(ch, "is_npc", False):
        return "NPCs cannot save."

    # Try to save the character
    try:
        # Call character's save method if it exists
        save_method = getattr(ch, "save", None)
        if callable(save_method):
            save_method()
            return "Saving. Remember that ROM has automatic saving now."
        else:
            # Fallback: Try to get session and save through persistence
            session = getattr(ch, "desc", None)
            if session and hasattr(session, "save_character"):
                session.save_character(ch)
                return "Saving. Remember that ROM has automatic saving now."
            return "Save failed - no save method available."
    except Exception as e:
        return f"Save failed: {e}"


def do_quit(ch: Character, args: str) -> str:
    """
    Quit the game.

    ROM Reference: src/act_comm.c lines 1496-1531 (do_quit)
    """
    # Can't quit while fighting
    if ch.position == Position.FIGHTING:
        return "No way! You are fighting."

    # Can't quit while position is too low
    if ch.position < Position.STUNNED:
        return "You're not DEAD yet."

    # Save before quitting
    if not getattr(ch, "is_npc", False):
        try:
            save_method = getattr(ch, "save", None)
            if callable(save_method):
                save_method()
        except Exception:
            pass  # Don't block quit on save failure

    # Get session and close it
    session = getattr(ch, "desc", None)
    if session:
        # Send goodbye message
        try:
            send_method = getattr(session, "send", None)
            if callable(send_method):
                send_method("May your travels be safe.")
        except Exception:
            pass

        # Close session
        try:
            close_method = getattr(session, "close", None)
            if callable(close_method):
                close_method()
        except Exception:
            pass

    return ""  # Empty return since session is closing


def do_score(ch: Character, args: str) -> str:
    """
    Display character statistics.

    ROM Reference: src/act_info.c lines 580-732 (do_score)
    """
    # Build score output mirroring ROM format
    lines = []

    # Name and title
    name = getattr(ch, "name", "Unknown")
    title = getattr(ch, "title", "")
    if title:
        lines.append(f"You are {name}{title}")
    else:
        lines.append(f"You are {name}")

    # Race, class, level
    race = getattr(ch, "race", "unknown")
    class_name = getattr(ch, "class_name", "unknown")
    level = getattr(ch, "level", 1)
    lines.append(f"Level {level}, {race} {class_name}")

    # Age and played time
    played = getattr(ch, "played", 0)
    hours = played // 3600
    lines.append(f"You have played for {hours} hours.")

    # HP, Mana, Movement
    hp = getattr(ch, "hit", 0)
    max_hp = getattr(ch, "max_hit", 0)
    mana = getattr(ch, "mana", 0)
    max_mana = getattr(ch, "max_mana", 0)
    move = getattr(ch, "move", 0)
    max_move = getattr(ch, "max_move", 0)

    lines.append(f"You have {hp}/{max_hp} hit, {mana}/{max_mana} mana, {move}/{max_move} movement.")

    # Stats
    perm_str = getattr(ch, "perm_str", 13)
    perm_int = getattr(ch, "perm_int", 13)
    perm_wis = getattr(ch, "perm_wis", 13)
    perm_dex = getattr(ch, "perm_dex", 13)
    perm_con = getattr(ch, "perm_con", 13)

    lines.append(f"Str: {perm_str}  Int: {perm_int}  Wis: {perm_wis}  Dex: {perm_dex}  Con: {perm_con}")

    # Armor class
    armor = getattr(ch, "armor", 100)
    lines.append(f"You are {_armor_class_description(armor)} armored.")

    # Hitroll and damroll
    hitroll = getattr(ch, "hitroll", 0)
    damroll = getattr(ch, "damroll", 0)
    lines.append(f"Hitroll: {hitroll}  Damroll: {damroll}")

    # Position
    position = ch.position
    lines.append(f"You are {position.name.lower()}.")

    # Carrying
    carry_weight = getattr(ch, "carry_weight", 0)
    carry_number = getattr(ch, "carry_number", 0)
    lines.append(f"You are carrying {carry_number} items with weight {carry_weight} pounds.")

    # Gold
    gold = getattr(ch, "gold", 0)
    silver = getattr(ch, "silver", 0)
    lines.append(f"You have {gold} gold and {silver} silver coins.")

    # Wimpy
    wimpy = getattr(ch, "wimpy", 0)
    if wimpy > 0:
        lines.append(f"Wimpy set to {wimpy} hit points.")

    return "\n".join(lines)


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
        # Get world instance
        from mud import world as world_module

        world = world_module.WORLD

        # Find recall room
        recall_room = world.rooms.get(recall_vnum)
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
