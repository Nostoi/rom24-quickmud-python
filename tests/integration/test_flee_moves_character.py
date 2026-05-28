"""PARALLEL-010 regression: do_flee must actually move the character.

Pre-fix: ``mud/commands/combat.py:683-688`` wrote to ``room.characters`` and
``new_room.characters`` — neither attribute exists (Room has ``people``). The
``hasattr(room, "characters")`` gate hid the remove silently and
``new_room.characters.append(char)`` raised ``AttributeError`` caught by the
broad ``try/except`` at lines 695-696, which surfaced a misleading
"Flee failed: 'Room' object has no attribute 'characters'" while
``char.move`` was still decremented at line 699.

Net pre-fix effect: character paid the move cost but did not actually move;
``room.people`` was never updated. The flee success path (combat-stop, exp
loss, room broadcast) ran but the actual room transition silently didn't.

Fix shape: use the canonical ``room.remove_character`` /
``new_room.add_character`` helpers (defined at ``mud/models/room.py:140, 157``)
so ``room.people`` membership is updated correctly.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_flee
from mud.models.constants import Position
from mud.registry import area_registry, room_registry
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _restore_world_registries():
    """Snapshot/restore the global world registries this module mutates.

    The flee test calls ``initialize_world()`` (which clears and reloads
    ``room_registry`` / ``area_registry`` from disk) and then mutates a *real*
    registered room's ``exits`` into a dict to exercise do_flee's dict-format
    branch. Both the populated registries and the dict-shaped exits used to leak
    across xdist worker boundaries: a later sibling test running ``game_tick()``
    would reset the leaked area and crash in ``_restore_exit_states`` when
    ``enumerate({"north": ...})`` yielded the string key and tried
    ``"north".exit_info = ...``. Snapshot before / restore after discards this
    test's corrupted Room objects and returns the registries to their pre-test
    state (AGENTS.md "Parallel test execution & isolation").
    """

    rooms_before = dict(room_registry)
    areas_before = dict(area_registry)
    yield
    room_registry.clear()
    room_registry.update(rooms_before)
    area_registry.clear()
    area_registry.update(areas_before)


def test_flee_moves_character_to_new_room(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful flee must place the character into the destination room's
    ``people`` list and remove them from the source room's ``people`` list.
    """
    initialize_world()

    src_vnum = 3001  # limbo
    src_char = create_test_character("Fleer", src_vnum)
    src_room = src_char.room
    assert src_room is not None

    opponent = create_test_character("Attacker", src_vnum)
    opponent.position = Position.FIGHTING

    # Find a different room in the registry to serve as the flee destination.
    from mud.registry import room_registry

    dst_vnum: int | None = None
    dst_room = None
    for vnum, room in room_registry.items():
        if vnum != src_vnum and room is not None:
            dst_vnum = vnum
            dst_room = room
            break
    assert dst_room is not None and dst_vnum is not None, "registry must have at least 2 rooms"

    # Wire a one-way exit from src to dst. Use the dict-style format that
    # do_flee's `isinstance(exit_data, dict)` branch accepts; `to_room` is
    # the destination vnum (do_flee looks it up via room_registry.get).
    src_room.exits = {"north": {"to_room": dst_vnum, "closed": False}}

    # Configure char for a successful flee.
    src_char.position = Position.FIGHTING
    src_char.hit = src_char.max_hit = 100
    src_char.wait = 0
    src_char.move = 100
    src_char.max_move = 100
    src_char.fighting = opponent

    # Force flee success deterministically: percent roll <= chance, and pick
    # the first (only) valid exit.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: lo)

    do_flee(src_char, "")

    assert src_char.room is dst_room, (
        f"PARALLEL-010: do_flee did not move char to destination room. "
        f"src_vnum={src_vnum}, dst_vnum={dst_vnum}, char.room={getattr(src_char.room, 'vnum', None)}."
    )
    assert src_char in dst_room.people, "char must be in dst_room.people after a successful flee"
    assert src_char not in src_room.people, "char must not be in src_room.people after a successful flee"
