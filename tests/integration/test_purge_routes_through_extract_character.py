"""PURGE-001 — ``do_purge`` must route through the canonical
``_extract_character`` chokepoint (``mud/mob_cmds.py``) instead of the
local stripped ``_extract_char`` stub in ``mud/commands/imm_load.py``.

ROM contract (``src/act_wiz.c:2574-2648 do_purge``)::

    extract_char (victim, TRUE);     /* line 2595 — purge room loop */
    extract_char (victim, TRUE);     /* line 2638 — purge named player */
    extract_char (victim, TRUE);     /* line 2646 — purge named NPC */

``extract_char`` in ROM (``src/handler.c:2103-2180``) runs the full
INV-020 cleanup chain: ``nuke_pets`` → ``die_follower`` →
``stop_fighting``. Python's local ``_extract_char`` stub only stops
fighting and unlinks from the room; charmed pets and group followers
leaked with dangling pointers when an immortal purged their master.

This test pins the pet-cleanup leg (INV-020). The follower leg is
already locked by INV-020's chain test grid — the same shared helper
covers both.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_load import do_purge
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_purge_room_nukes_pets() -> None:
    """No-arg ``purge`` must run the INV-020 cleanup chain on each NPC.

    ROM ``src/act_wiz.c:2584-2607`` iterates ``ch->in_room->people``
    and calls ``extract_char(victim, TRUE)`` (line 2595) for each
    non-NOPURGE NPC. ``extract_char`` runs ``nuke_pets`` first
    (``src/handler.c:2115``). Python's stub bypasses this — the
    purged master's charmed pet keeps its dangling pointer and stays
    in the registry.
    """
    room = Room(vnum=99961, name="Purge pet probe")
    immortal = Character(name="Immortal", is_npc=False, position=Position.STANDING)
    immortal.level = 60
    immortal.trust = 60

    master = Character(name="Master", is_npc=True, position=Position.STANDING)
    master.short_descr = "the pet master"
    master.level = 5

    pet = Character(name="Pet", is_npc=True, position=Position.STANDING)
    pet.short_descr = "a charmed pet"
    pet.level = 3
    pet.affected_by = int(AffectFlag.CHARM)
    pet.master = master
    pet.leader = master
    master.pet = pet

    room.add_character(immortal)
    room.add_character(master)
    room.add_character(pet)
    character_registry.extend([immortal, master, pet])

    do_purge(immortal, "")

    assert master not in room.people, "Purged NPC master should be unlinked from room.people."
    assert pet not in character_registry, (
        "ROM extract_char calls nuke_pets first (handler.c:2115). The "
        "charmed pet must be extracted alongside its master. Python's "
        "stripped _extract_char stub skipped this, leaking the pet."
    )
