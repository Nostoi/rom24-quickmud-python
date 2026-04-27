"""Integration tests for ``do_mpflee`` (MOBprog ``flee`` script command).

ROM C reference: ``src/mob_cmds.c:1260-1287`` — ROM calls
``move_char(ch, door, FALSE)`` so the canonical movement pipeline runs
(leave/arrive broadcasts, mp_exit/entry triggers, autoexits, etc.).

Closes MOBCMD-010.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpflee
from mud.models.character import Character
from mud.models.constants import Direction, Position
from mud.models.room import Exit, Room


@pytest.fixture
def room_pair() -> tuple[Room, Room]:
    src = Room(vnum=9601, name="Flee Source")
    dst = Room(vnum=9602, name="Flee Dest")
    src.exits[int(Direction.NORTH)] = Exit(to_room=dst)
    return src, dst


@pytest.fixture
def script_mob(room_pair: tuple[Room, Room]) -> Character:
    src, _ = room_pair
    mob = Character(name="Fleer", is_npc=True)
    mob.position = Position.STANDING
    mob.level = 30
    src.add_character(mob)
    return mob


@pytest.fixture
def witness(room_pair: tuple[Room, Room]) -> Character:
    src, _ = room_pair
    obs = Character(name="Watcher", is_npc=False)
    obs.position = Position.STANDING
    src.add_character(obs)
    return obs


class TestMpFleeUsesMoveChar:
    """MOBCMD-010: ``do_mpflee`` must route through ``move_character`` so
    leave/arrive broadcasts and movement-pipeline side effects fire,
    mirroring ROM ``src/mob_cmds.c:1283`` (``move_char(ch, door, FALSE)``).
    The previous implementation called the silent ``_move_to_room`` helper,
    so room occupants saw nothing.
    """

    def test_flee_broadcasts_departure_to_old_room(self, script_mob, witness, room_pair):
        src, dst = room_pair

        do_mpflee(script_mob, "")

        # Witness: a watcher left behind in the source room must see the
        # "$n leaves <direction>." departure broadcast that move_character
        # emits via broadcast_room (mud/world/movement.py:443).
        assert script_mob.room is dst, "mob should have moved to dst"
        assert any("leaves" in msg for msg in witness.messages), (
            f"witness saw {witness.messages!r}; expected a 'leaves north'"
            " broadcast from the canonical movement pipeline. The old"
            " implementation used _move_to_room which is silent."
        )
