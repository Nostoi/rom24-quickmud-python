"""INV-047 — extract_char clears the ROM `mprog_target` pointer (quirk-faithful).

ROM `extract_char` (`src/handler.c:2151-2157`) walks `char_list` after unlinking
the extracted char and nullifies two single-target pointers:

    for (wch = char_list; wch != NULL; wch = wch->next)
    {
        if (wch->reply == ch)
            wch->reply = NULL;
        if (ch->mprog_target == wch)
            wch->mprog_target = NULL;
    }

The `reply` line is correct dangling-pointer hygiene (already mirrored in
`mud/mob_cmds.py:_extract_character`). The `mprog_target` line is a **famous ROM
2.4b6 bug** that survived into the base distribution: it tests
`ch->mprog_target == wch` (does the *extracted* char target wch?) and then clears
`wch->mprog_target` (wch's OWN target) — so it does NOT clear other mobs whose
`mprog_target` points *at* the extracted char, and it DOES wipe the remembered
target of whoever the extracted char was targeting.

Per AGENTS.md ("replicate ROM quirks exactly"), the faithful port mirrors the
buggy line verbatim, not the "corrected" `wch->mprog_target == ch` version many
ROM derivatives shipped. Python previously implemented neither half for
`mprog_target` (a `# would go here if needed` TODO).

This test pins BOTH halves of the observable behavior.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import _extract_character
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def isolated_registry():
    saved = list(character_registry)
    character_registry.clear()
    yield character_registry
    character_registry[:] = saved


def _mob(room: Room, name: str, registry: list[Character]) -> Character:
    mob = Character(name=name, is_npc=True)
    mob.position = Position.STANDING
    mob.hit = 100
    mob.max_hit = 100
    room.add_character(mob)
    registry.append(mob)
    return mob


def test_extract_clears_targets_remembered_victim(isolated_registry) -> None:
    """ROM handler.c:2155-2156 — extracting A (whose mprog_target is B) clears
    B's OWN mprog_target. The quirk fires on `ch->mprog_target == wch`.
    """
    room = Room(vnum=9830, name="Extract mprog room")
    a = _mob(room, "Alpha", isolated_registry)
    b = _mob(room, "Beta", isolated_registry)

    a.mprog_target = b  # A remembers B
    b.mprog_target = b  # B has some remembered target of its own

    _extract_character(a, fPull=True)

    assert b.mprog_target is None, (
        "ROM extract_char (handler.c:2155-2156) clears wch->mprog_target when "
        "ch->mprog_target == wch; extracting A (who targeted B) must wipe B's "
        "remembered target."
    )


def test_extract_does_not_clear_pointers_aimed_at_victim(isolated_registry) -> None:
    """ROM's quirk does NOT clear mobs whose mprog_target points AT the extracted
    char — the 'corrected' `wch->mprog_target == ch` cleanup is absent in 2.4b6.
    A mob C that remembered the extracted A keeps its (now-dangling) pointer.
    """
    room = Room(vnum=9831, name="Extract mprog room 2")
    a = _mob(room, "Alpha", isolated_registry)
    c = _mob(room, "Gamma", isolated_registry)

    c.mprog_target = a  # C remembers A (the char being extracted)
    a.mprog_target = None  # A targets no one, so the quirk-branch won't fire

    _extract_character(a, fPull=True)

    assert c.mprog_target is a, (
        "ROM extract_char does NOT clear wch->mprog_target when wch->mprog_target "
        "== ch (the 2.4b6 bug); C's pointer at the extracted A must survive."
    )
