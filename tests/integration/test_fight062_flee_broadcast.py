"""FIGHT-062 — do_flee "$n has fled!" broadcast goes through the act() system.

ROM ``do_flee`` (``src/fight.c:3005-3007``) temporarily restores
``ch->in_room = was_in`` and calls ``act("$n has fled!", ch, NULL, NULL,
TO_ROOM)`` — per-recipient ``$n`` PERS masking (an invisible fleer masks to
"someone") delivered through the standard channel, with TRIG_ACT for NPC
witnesses. The Python ``mud/commands/combat.py:do_flee`` baked ``char.name`` and
iterated ``other.desc.send`` directly, so descriptor-less occupants (NPCs / test
characters) — including the opponent left behind — received nothing, and an
invisible fleer leaked their name. Same class as REPORT-001.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_flee
from mud.models.constants import Position
from mud.models.room import Exit
from mud.registry import area_registry, room_registry
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _restore_world_registries():
    rooms_before = dict(room_registry)
    areas_before = dict(area_registry)
    yield
    room_registry.clear()
    room_registry.update(rooms_before)
    area_registry.clear()
    area_registry.update(areas_before)


def test_flee_broadcasts_to_descriptorless_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    """The opponent left behind (no live descriptor) must receive '<fleer> has fled!'."""
    initialize_world()

    src_vnum = 3001
    fleer = create_test_character("Fleer", src_vnum)
    src_room = fleer.room
    assert src_room is not None

    opponent = create_test_character("Attacker", src_vnum)
    opponent.position = Position.FIGHTING
    opponent.messages = []

    # Destination room.
    dst_room = next(r for v, r in room_registry.items() if v != src_vnum and r is not None)

    exits_list = [None] * 6
    exits_list[0] = Exit(to_room=dst_room, exit_info=0, keyword="north", key=0)
    src_room.exits = exits_list

    fleer.position = Position.FIGHTING
    fleer.hit = fleer.max_hit = 100
    fleer.wait = 0
    fleer.move = fleer.max_move = 100
    fleer.fighting = opponent

    monkeypatch.setattr(rng_mm, "number_door", lambda: 0)

    do_flee(fleer, "")

    # ROM act("$n has fled!") delivered to the fled-from room, $n -> "Fleer".
    joined = "\n".join(opponent.messages)
    assert "Fleer has fled!" in joined, f"witness did not receive the flee broadcast: {opponent.messages!r}"
