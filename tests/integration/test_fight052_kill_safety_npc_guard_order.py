"""FIGHT-052 — _kill_safety_message inverts NPC-attacker-vs-PC guard ordering vs ROM.

ROM src/fight.c:1080-1093 — is_safe NPC-attacker-vs-PC branch checks safe-room FIRST,
then charmed-mob guard:

    if (IS_NPC(ch)) {
        /* safe room check */        ← line 1083 (FIRST)
        if (IS_SET(..., ROOM_SAFE)) {
            send_to_char("Not in this room.\n\r", ch);
            return TRUE;
        }
        /* charmed mobs cannot attack players */   ← line 1087 (SECOND)
        if (IS_AFFECTED(ch, AFF_CHARM) && ch->master != NULL
                && ch->master->fighting != victim) {
            send_to_char("Players are your friends!\n\r", ch);
            return TRUE;
        }
    }

Python _kill_safety_message (mud/commands/combat.py:70-76) has the order inverted:
charmed-mob guard FIRST, safe-room SECOND.

Corner case: charmed mob in safe room attacking a PC whose master is NOT fighting that PC.
ROM → "Not in this room." (safe-room wins)
Python (pre-fix) → "Players are your friends!" (charmed-mob wins, wrong message)
"""

from __future__ import annotations

import pytest

from mud.commands.combat import _kill_safety_message
from mud.models.character import Character
from mud.models.constants import AffectFlag, RoomFlag
from mud.world import create_test_character, initialize_world

_SAFE_ROOM = 3001  # a ROOM_SAFE room — need to find/verify one exists or patch
_PLAIN_ROOM = 2300  # a non-safe room in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str, room_vnum: int = _PLAIN_ROOM) -> Character:
    ch = create_test_character(name, room_vnum)
    ch.is_npc = False
    ch.level = 20
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def _make_npc(name: str, room_vnum: int = _PLAIN_ROOM) -> Character:
    ch = create_test_character(name, room_vnum)
    ch.is_npc = True
    ch.level = 20
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def test_fight052_charmed_npc_in_safe_room_returns_safe_room_message() -> None:
    """Corner case: charmed NPC in a safe room attacking a PC whose master isn't fighting them.

    ROM src/fight.c:1083 safe-room check fires BEFORE the charmed-mob check at :1087.
    Result should be "Not in this room." not "Players are your friends!".
    """
    # mirrors ROM src/fight.c:1083-1093 — safe-room wins over charmed-mob guard
    master = _make_pc("Master")
    other_target = _make_pc("OtherTarget")
    master.fighting = other_target  # master is fighting someone else

    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = master

    # Put charmed mob in a safe room
    victim = _make_pc("Victim")
    room = getattr(victim, "room", None)
    if room is not None:
        room.room_flags = int(RoomFlag.ROOM_SAFE)

    result = _kill_safety_message(charmed_mob, victim)

    assert result == "Not in this room.", (
        f"Expected 'Not in this room.' (safe-room check, ROM :1083); got {result!r}. "
        "ROM src/fight.c:1083 safe-room check fires before the charmed-mob guard at :1087 — "
        "when a charmed NPC is in a safe room, safe-room message must take priority."
    )
