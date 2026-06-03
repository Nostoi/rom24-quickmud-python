"""SLAY-001 — ``do_slay`` must route through ``raw_kill`` so a slain NPC
produces a corpse, fires ``death_cry``, drops gold/silver, and runs the
INV-020 cleanup chain (nuke_pets + die_follower).

ROM contract (``src/fight.c:3252-3287 do_slay``)::

    act ("{1You slay $M in cold blood!{x", ch, NULL, victim, TO_CHAR);
    act ("{1$n slays you in cold blood!{x", ch, NULL, victim, TO_VICT);
    act ("{1$n slays $N in cold blood!{x", ch, NULL, victim, TO_NOTVICT);
    raw_kill (victim);

Python pre-fix called a local ``_extract_char`` stub in
``mud/commands/imm_load.py`` that only stops fighting and unlinks from
the room — no corpse, no death_cry, no gold drop, no INV-020 cleanup
(charmed pets and group followers leak with dangling pointers).

This test pins the corpse contract — the most visible side-effect of
the routing fix. The pet/follower leg is already locked by INV-020's
chain test grid (the fix shares the helper, so once slay routes through
raw_kill all four INV-020 sub-contracts come along for free). The
missing TO_VICT/TO_NOTVICT broadcasts are filed as a separate gap.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_load import do_slay
from mud.models.character import Character, character_registry
from mud.models.constants import ItemType, Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_slay_produces_corpse_for_npc() -> None:
    """``do_slay`` on an NPC must produce a corpse in the room.

    ROM ``src/fight.c:3285`` calls ``raw_kill(victim)`` which invokes
    ``make_corpse`` (``src/fight.c:1850+``). Python's stub
    ``_extract_char`` was bypassing this; the slain NPC vanished
    silently with no corpse, no inventory drop, no death_cry.
    """
    room = Room(vnum=99960, name="Slay corpse probe")
    immortal = Character(name="Immortal", is_npc=False, position=Position.STANDING)
    immortal.level = 60
    immortal.trust = 60
    npc = Character(name="Victim", is_npc=True, position=Position.STANDING)
    npc.short_descr = "the test mob"
    npc.level = 1
    npc.hit = 100
    npc.max_hit = 100
    room.add_character(immortal)
    room.add_character(npc)
    character_registry.extend([immortal, npc])

    do_slay(immortal, "Victim")

    corpse = next(
        (obj for obj in getattr(room, "contents", []) if getattr(obj, "item_type", None) == int(ItemType.CORPSE_NPC)),
        None,
    )
    assert corpse is not None, (
        "ROM src/fight.c:3285 raw_kill(victim) → make_corpse spawns an "
        "NPC corpse into the room. Python do_slay called a stripped "
        "_extract_char stub instead; no corpse landed in room.contents. "
        f"Room contents: {[getattr(o, 'name', o) for o in getattr(room, 'contents', [])]}"
    )
    assert npc not in room.people, (
        "ROM src/fight.c raw_kill unlinks the victim from char_list. Victim should have been removed from room.people."
    )
