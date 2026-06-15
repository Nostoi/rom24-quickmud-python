"""CONSIDER-002 / INV-050 — do_consider surfaces ROM is_safe's context line.

ROM ``do_consider`` (src/act_info.c:2490-2493) is::

    if (is_safe (ch, victim))
    {
        send_to_char ("Don't even think about it.\n\r", ch);
        return;
    }

ROM ``is_safe`` (src/fight.c:1018-1124) writes its OWN context line via
``send_to_char``/``act`` *before* returning TRUE — e.g. for a healer/trainer
victim it sends "I don't think Mota would approve.".  So a blocked ``consider``
shows TWO lines: the is_safe context line, then "Don't even think about it.".

Python ``do_consider`` routed through the silent bool ``combat.safety.is_safe``
(which writes no message) and returned only "Don't even think about it." —
dropping ROM's context line.  This is the INV-050 convergence: route the gate
through the faithful mirror ``_kill_safety_message`` so the player sees both.
"""

from __future__ import annotations

import pytest

from mud.commands.consider import do_consider
from mud.models.character import Character
from mud.models.constants import ActFlag, Sector
from mud.models.room import Room


@pytest.fixture
def room():
    r = Room(vnum=3001)
    r.sector_type = int(Sector.INSIDE)
    r.room_flags = 0
    r.light = 1
    return r


def test_consider_healer_shows_context_line_and_dont_think(room) -> None:
    # mirrors ROM src/act_info.c:2490 + src/fight.c:1046 — is_safe sends
    # "I don't think Mota would approve." THEN do_consider sends the override.
    char = Character()
    char.name = "Considerer"
    char.level = 10
    char.is_npc = False
    char.room = room
    room.add_character(char)

    healer = Character()
    healer.name = "healer"
    healer.is_npc = True
    healer.level = 10
    healer.act = int(ActFlag.IS_HEALER)
    healer.room = room
    room.add_character(healer)

    result = do_consider(char, "healer")

    assert "Mota would approve" in result, f"expected ROM is_safe context line, got {result!r}"
    assert "Don't even think about it." in result, f"expected ROM override line, got {result!r}"
