"""FIGHT-070 — do_bash must surface ROM is_safe()'s context message.

ROM ``is_safe`` (src/fight.c:1018-1124) is a bool that *also* writes the
rejection line to the attacker's descriptor via ``send_to_char`` before it
returns TRUE.  ``do_bash`` (src/fight.c:2405-2406) relies on that::

    if (is_safe (ch, victim))
        return;                 /* message already sent inside is_safe */

So bashing an NPC in a ROOM_SAFE room makes ROM print "Not in this room."
(src/fight.c:1036) and abort the skill.

Python had split ROM's is_safe into two objects: a *silent* bool
(``mud/combat/safety.py:is_safe``) and a *message-returning* faithful mirror
(``combat.py:_kill_safety_message``).  ``do_bash`` called the silent bool and
``return ""`` — so the whole skill was correctly gated (FIGHT-067) but the
player saw **nothing**, where ROM gives them the reason.  This test asserts the
context line is surfaced.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_bash
from mud.models.constants import Position, RoomFlag
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_bash_npc_in_safe_room_surfaces_not_in_this_room() -> None:
    # mirrors ROM src/fight.c:1034-1037 — is_safe sends "Not in this room."
    # for an NPC victim in a ROOM_SAFE room, then do_bash returns (2405-2406).
    attacker = create_test_character("Basher", 3001)
    victim = create_test_character("Mark", 3001)

    attacker.skills["bash"] = 100
    attacker.wait = 0

    # NPC victim, standing (passes the position gate at src/fight.c:2392).
    victim.is_npc = True
    victim.position = int(Position.STANDING)

    # ROOM_SAFE → is_safe's NPC-victim branch sends "Not in this room."
    room = attacker.room
    room.room_flags = int(getattr(room, "room_flags", 0) or 0) | int(RoomFlag.ROOM_SAFE)

    result = do_bash(attacker, "Mark")

    assert result == "Not in this room.", (
        f"do_bash swallowed ROM is_safe()'s context message (FIGHT-070): expected 'Not in this room.', got {result!r}"
    )
