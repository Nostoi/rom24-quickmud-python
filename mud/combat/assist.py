"""
Combat assist mechanics - auto-assist for group combat.

ROM Reference: src/fight.c check_assist (lines 105-181)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.characters import is_same_group
from mud.combat.engine import multi_hit, is_good, is_evil, is_neutral
from mud.combat.safety import is_safe
from mud.models.constants import AffectFlag, OffFlag, PlayerFlag
from mud.utils import rng_mm
from mud.world.vision import can_see_character

if TYPE_CHECKING:
    from mud.models.character import Character


def check_assist(ch: Character, victim: Character) -> None:
    """
    Check for auto-assist in combat following ROM C src/fight.c:check_assist (L105-181).

    This function is called when 'ch' attacks 'victim' to see if anyone in the room
    will automatically assist either side.

    Handles six assist types:
    1. ASSIST_PLAYERS: Mobs help players fighting weaker mobs (lines 116-124)
    2. PLR_AUTOASSIST: Players auto-assist group members (lines 126-135)
    3. ASSIST_ALL: Mobs assist any mob in the room (line 141)
    4. ASSIST_RACE: Mobs assist same race (lines 143-144)
    5. ASSIST_ALIGN: Mobs assist same alignment (lines 145-148)
    6. ASSIST_VNUM: Mobs assist same vnum (lines 149-150)

    Args:
        ch: Character currently attacking (the aggressor)
        victim: Character being attacked by ch

    ROM C Reference:
        src/fight.c:105-181
    """
    # Get all characters in the same room
    room = getattr(ch, "room", None)
    if not room:
        return

    people_in_room = getattr(room, "people", [])
    if not people_in_room:
        return

    # Loop through all characters in the room
    # NOTE: We need to be careful about list modification during iteration
    # ROM uses rch_next pattern to handle this
    for rch in list(people_in_room):  # Create a copy to avoid modification issues
        # Skip if not awake or already fighting
        if not _is_awake(rch):
            continue

        if getattr(rch, "fighting", None) is not None:
            continue

        # --- ASSIST_PLAYERS: Mobs help players fighting weaker mobs (ROM lines 116-124) ---
        if not _is_npc(ch) and _is_npc(rch):
            rch_off_flags = getattr(rch, "off_flags", 0)
            if rch_off_flags & OffFlag.ASSIST_PLAYERS:
                rch_level = getattr(rch, "level", 1)
                victim_level = getattr(victim, "level", 1)
                if rch_level + 6 > victim_level:
                    _emote(rch, "screams and attacks!")
                    multi_hit(rch, victim, None)
                    continue

        # --- PCs next (ROM lines 126-135) ---
        # Player characters or charmed mobs can auto-assist
        if not _is_npc(ch) or _is_affected(ch, AffectFlag.CHARM):
            # Check if rch is a player with autoassist or a charmed mob
            rch_act = getattr(rch, "act", 0)
            is_rch_autoassist = not _is_npc(rch) and (rch_act & PlayerFlag.AUTOASSIST)
            is_rch_charmed = _is_affected(rch, AffectFlag.CHARM)

            if (is_rch_autoassist or is_rch_charmed) and is_same_group(ch, rch):
                if not is_safe(rch, victim):
                    multi_hit(rch, victim, None)

            continue

        # --- NPC assist cases (ROM lines 137-178) ---
        # Only NPCs that aren't charmed can use these assist types
        if _is_npc(ch) and not _is_affected(ch, AffectFlag.CHARM):
            if not _is_npc(rch):
                continue  # rch must be NPC for these assist types

            rch_off_flags = getattr(rch, "off_flags", 0)
            should_assist = False

            # ASSIST_ALL: Assist any mob
            if rch_off_flags & OffFlag.ASSIST_ALL:
                should_assist = True

            # ASSIST_RACE: Assist same race
            elif rch_off_flags & OffFlag.ASSIST_RACE:
                ch_race = getattr(ch, "race", None)
                rch_race = getattr(rch, "race", None)
                if ch_race and rch_race and ch_race == rch_race:
                    should_assist = True

            # ASSIST_ALIGN: Assist same alignment
            elif rch_off_flags & OffFlag.ASSIST_ALIGN:
                if (
                    (is_good(rch) and is_good(ch))
                    or (is_evil(rch) and is_evil(ch))
                    or (is_neutral(rch) and is_neutral(ch))
                ):
                    should_assist = True

            # ASSIST_VNUM: Assist same vnum (same mob prototype)
            elif rch_off_flags & OffFlag.ASSIST_VNUM:
                ch_vnum = getattr(ch, "vnum", None)
                rch_vnum = getattr(rch, "vnum", None)
                if ch_vnum is not None and rch_vnum is not None and ch_vnum == rch_vnum:
                    should_assist = True

            # Group assist: NPCs in same group help each other
            ch_group = getattr(ch, "group", None)
            rch_group = getattr(rch, "group", None)
            if ch_group and rch_group and ch_group == rch_group:
                should_assist = True

            if should_assist:
                # ROM lines 156-157: 50% chance to skip assist
                if rng_mm.number_bits(1) == 0:
                    continue

                # ROM lines 159-170: Randomly select target from victim's group
                target = None
                number = 0

                # Use reservoir sampling to pick random group member
                for vch in list(people_in_room):
                    if can_see_character(rch, vch) and is_same_group(vch, victim):
                        if rng_mm.number_range(0, number) == 0:
                            target = vch
                        number += 1

                # ROM lines 172-176: Attack the selected target
                if target is not None:
                    _emote(rch, "screams and attacks!")
                    multi_hit(rch, target, None)


def _is_awake(char: Character) -> bool:
    """Check if character is awake (ROM IS_AWAKE macro)."""
    from mud.models.constants import Position

    position = getattr(char, "position", Position.STANDING)
    return position > Position.SLEEPING


def _is_npc(char: Character) -> bool:
    """Check if character is NPC (ROM IS_NPC macro)."""
    return getattr(char, "is_npc", False)


def _is_affected(char: Character, flag: AffectFlag) -> bool:
    """Check if character has affect flag (ROM IS_AFFECTED macro)."""
    affected_by = getattr(char, "affected_by", 0)
    return bool(affected_by & flag)


def _emote(char: Character, message: str) -> None:
    """
    Make character perform an emote.

    ROM C uses: do_function(rch, &do_emote, "screams and attacks!");
    Python equivalent: Send message to room.
    """
    from mud.models.social import expand_placeholders

    room = getattr(char, "room", None)
    if not room:
        return

    # Format: "Name screams and attacks!"
    char_name = getattr(char, "name", "Someone")
    full_message = f"{char_name} {message}"

    # Send to everyone in the room
    people = getattr(room, "people", [])
    for person in people:
        if person != char:
            _send_to_char(person, full_message)


def _send_to_char(char: Character, message: str) -> None:
    """Send a message to a character."""
    send = getattr(char, "send", None)
    if callable(send):
        send(message + "\n")
    else:
        # Fallback: add to messages list if it exists
        messages = getattr(char, "messages", None)
        if isinstance(messages, list):
            messages.append(message + "\n")
