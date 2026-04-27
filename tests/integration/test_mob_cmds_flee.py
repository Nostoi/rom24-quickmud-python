"""Integration tests for ``do_mpflee`` (MOBprog ``flee`` script command).

ROM C reference: ``src/mob_cmds.c:1260-1287`` — ROM calls
``move_char(ch, door, FALSE)`` so the canonical movement pipeline runs
(leave/arrive broadcasts, mp_exit/entry triggers, autoexits, etc.) and
runs 6 random_door() attempts before giving up.

Closes MOBCMD-010, MOBCMD-008.
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


class TestMpFleeRandomDoor:
    """MOBCMD-008: ``do_mpflee`` must pick a random door across 6 attempts
    rather than iterating exits in list order, mirroring ROM
    ``src/mob_cmds.c:1272-1286``::

        for (attempt = 0; attempt < 6; attempt++)
        {
            door = number_door();
            ...
        }

    Pre-fix the loop walked ``room.exits`` in list order so the first valid
    exit always won. Post-fix the rng-driven door distribution selects a
    different exit across many runs.
    """

    def test_random_door_distribution_is_not_first_exit_only(self):
        # Build a fresh room with 4 valid exits each run; reseed and call
        # do_mpflee enough times to assert at least 2 distinct exits chosen.
        from mud.utils import rng_mm

        chosen: set[int] = set()
        for seed in range(1, 30):
            src = Room(vnum=9700, name="Flee Multi Source")
            dests: dict[int, Room] = {}
            for d in (Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST):
                room = Room(vnum=9700 + int(d) + 1, name=f"Dest {int(d)}")
                src.exits[int(d)] = Exit(to_room=room)
                dests[int(d)] = room

            mob = Character(name="Fleer", is_npc=True)
            mob.position = Position.STANDING
            mob.level = 30
            src.add_character(mob)

            rng_mm.seed_mm(seed)
            do_mpflee(mob, "")

            for d_int, room in dests.items():
                if mob.room is room:
                    chosen.add(d_int)
                    break

        # Pre-fix: iteration always picked Direction.NORTH (first non-None).
        # Post-fix: random_door() distributes across all 4 valid exits, so
        # we must observe more than just NORTH across many seeds.
        assert len(chosen) >= 2, (
            f"only directions {chosen!r} ever chosen across 30 seeds; expected"
            " random_door() to distribute across multiple exits."
        )
