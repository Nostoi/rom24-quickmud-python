"""
Combat assist mechanics - auto-assist for group combat.

ROM Reference: src/fight.c check_assist (lines 105-181)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.characters import is_same_group
from mud.combat.engine import char_list_walk_from_room_head, is_evil, is_good, is_neutral, multi_hit
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
        if not rch.is_awake():
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
                # INV-050: route through the faithful ROM is_safe() mirror
                # (_kill_safety_message, src/fight.c:1018-1124) rather than the
                # silent bool combat.safety.is_safe. ROM check_assist gates on
                # `!is_safe(rch, victim)` (src/fight.c:131); is_safe writes its
                # OWN rejection line to rch via send_to_char BEFORE returning
                # TRUE (e.g. "Join a clan if you want to kill players." for a
                # non-clan PC autoassister) — so a blocked assister sees the
                # line. A None return == not safe → rch assists. The silent bool
                # lacked the PC clan ladder, so non-clan PCs wrongly auto-assisted
                # in PvP. (Function-local import avoids an engine→command cycle.)
                from mud.commands.combat import _kill_safety_message

                safety_message = _kill_safety_message(rch, victim)
                if safety_message is None:
                    multi_hit(rch, victim, None)
                else:
                    _send_to_char(rch, safety_message + "\n")

            continue

        # --- NPC assist cases (ROM lines 137-178) ---
        # Only NPCs that aren't charmed can use these assist types
        if _is_npc(ch) and not _is_affected(ch, AffectFlag.CHARM):
            if not _is_npc(rch):
                continue  # rch must be NPC for these assist types

            rch_off_flags = getattr(rch, "off_flags", 0)
            should_assist = False

            # mirroring ROM src/fight.c:141-150 — all five assist conditions are a
            # flat || OR chain; C evaluates each until one is true.  Python's
            # `elif` would enter the ASSIST_RACE branch (flag set) and skip
            # ASSIST_ALIGN/ASSIST_VNUM even when the inner race predicate fails.
            # Independent `if` checks restore the ROM || semantics.

            # ASSIST_ALL: Assist any mob
            if rch_off_flags & OffFlag.ASSIST_ALL:
                should_assist = True

            # ASSIST_RACE: Assist same race (ROM src/fight.c:143-144)
            if rch_off_flags & OffFlag.ASSIST_RACE:
                ch_race = getattr(ch, "race", None)
                rch_race = getattr(rch, "race", None)
                if ch_race and rch_race and ch_race == rch_race:
                    should_assist = True

            # ASSIST_ALIGN: Assist same alignment (ROM src/fight.c:145-148)
            if rch_off_flags & OffFlag.ASSIST_ALIGN:
                if (
                    (is_good(rch) and is_good(ch))
                    or (is_evil(rch) and is_evil(ch))
                    or (is_neutral(rch) and is_neutral(ch))
                ):
                    should_assist = True

            # ASSIST_VNUM: Assist same vnum/mob prototype (ROM src/fight.c:149-150)
            if rch_off_flags & OffFlag.ASSIST_VNUM:
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

                # ROM src/fight.c:159-170 — number++ is INSIDE the selection block;
                # it only increments when a new target is chosen, not on every
                # visible group member. This matches ROM's biased selection distribution
                # and, critically, keeps the shared MM RNG stream in sync.
                #
                # FIGHT-095 / INV-045 — the iteration DOMAIN: ROM's loop is
                # `for (vch = ch->in_room->people; vch; vch = vch->next)`
                # (src/fight.c:161) — it SEEDS at the room people-list head
                # (newest arrival; char_to_room head-inserts) but follows the
                # GLOBAL char_list link (`->next`, NOT `->next_in_room`), a
                # 2.4b6 quirk. char_list is head-inserted at creation
                # (src/db.c:2256-2257, newest-first), so the visited set is the
                # room head plus every char CREATED BEFORE it — including chars
                # in OTHER rooms (a cross-room reservoir pick then whiffs in
                # one_hit's room guard, FIGHT-097) and EXCLUDING same-room
                # chars newer than the head. character_registry is append-order
                # (oldest-first), the reverse of char_list, so the walk is the
                # reversed registry slice up to the room head's index (the
                # GROUP-006 / INV-045 fix pattern). C-oracle ground truth:
                # tools/diff_harness/scenarios/check_assist_cross_room.json.
                for vch in char_list_walk_from_room_head(ch):
                    if can_see_character(rch, vch) and is_same_group(vch, victim):
                        if rng_mm.number_range(0, number) == 0:
                            target = vch
                            number += 1  # mirroring ROM src/fight.c:165

                # ROM lines 172-176: Attack the selected target
                if target is not None:
                    _emote(rch, "screams and attacks!")
                    multi_hit(rch, target, None)


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

    ROM C: do_function(rch, &do_emote, "screams and attacks!") — do_emote
    (src/act_comm.c) renders act("$n $T", ch, NULL, argument, TO_ROOM) plus the
    same line TO_CHAR. act_new resolves $n via PERS (NPC short_descr, can-see
    gated) and upper-cases the line start, so observers see "The drunk screams
    and attacks!" and the emoting char receives its own line (FIGHT-096).
    """
    from mud.utils.act import act_format

    room = getattr(char, "room", None)
    if not room:
        return

    # TO_ROOM (everyone but char) + TO_CHAR (char) == every room occupant.
    # mirroring ROM src/act_comm.c:do_emote
    for person in getattr(room, "people", []):
        _send_to_char(person, act_format(f"$n {message}", recipient=person, actor=char) + "\n")


# DUPL-001b — canonical at mud/utils/messaging.py:send_to_char_buffered.
from mud.utils.messaging import send_to_char_buffered as _send_to_char  # noqa: E402
