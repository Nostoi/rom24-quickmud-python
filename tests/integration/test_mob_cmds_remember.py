"""Integration tests for ``do_mpremember`` (MOBprog ``remember`` script command).

ROM C reference: ``src/mob_cmds.c:1155-1164`` —

    void do_mpremember (CHAR_DATA * ch, char *argument)
    {
        ...
        if (arg[0] != '\\0')
            ch->mprog_target = get_char_world (ch, arg);
        else
            bug (...);
    }

ROM assigns ``mprog_target`` **unconditionally** to the result of
``get_char_world`` whenever a (non-empty) argument is given. When the lookup
fails, ``get_char_world`` returns ``NULL``, so ROM *clears* the remembered
target. Python's ``do_mpremember`` early-returned on a failed lookup and left a
stale previous target in place — the MOBCMD-019 divergence.

Closes MOBCMD-019.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpforget, do_mpremember
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def remember_room() -> Room:
    return Room(vnum=9820, name="Remember Test Room")


@pytest.fixture
def isolated_registry():
    """Replace character_registry contents so ``_find_char_world`` (which walks
    the global registry) only sees this test's actors, restoring on teardown.
    """
    saved = list(character_registry)
    character_registry.clear()
    yield character_registry
    character_registry[:] = saved


def _mob(room: Room) -> Character:
    mob = Character(name="ScriptMob", is_npc=True)
    mob.position = Position.STANDING
    room.add_character(mob)
    return mob


def _pc(room: Room, name: str, registry: list[Character]) -> Character:
    pc = Character(name=name, is_npc=False)
    pc.position = Position.STANDING
    room.add_character(pc)
    registry.append(pc)
    return pc


def test_remember_sets_target(remember_room: Room, isolated_registry) -> None:
    """A resolvable ``remember <name>`` stores the matched char as mprog_target."""
    mob = _mob(remember_room)
    victim = _pc(remember_room, "Bob", isolated_registry)

    do_mpremember(mob, "Bob")

    assert mob.mprog_target is victim


def test_remember_unknown_name_clears_stale_target(remember_room: Room, isolated_registry) -> None:
    """ROM src/mob_cmds.c:1160 — ``ch->mprog_target = get_char_world(ch, arg)``
    is an unconditional assignment. A non-empty argument that resolves to no one
    must CLEAR the previously remembered target (get_char_world returns NULL),
    not leave it stale.
    """
    mob = _mob(remember_room)
    victim = _pc(remember_room, "Bob", isolated_registry)

    do_mpremember(mob, "Bob")
    assert mob.mprog_target is victim

    # Bob leaves the world; the script now tries to remember someone absent.
    do_mpremember(mob, "Nobody")

    assert mob.mprog_target is None, (
        "ROM assigns mprog_target = get_char_world(ch, arg) unconditionally; a "
        "failed lookup returns NULL and clears the target — Python left it stale."
    )


def test_remember_empty_arg_leaves_target_unchanged(remember_room: Room, isolated_registry) -> None:
    """ROM src/mob_cmds.c:1159 — an empty argument hits the ``bug()`` branch and
    does NOT touch mprog_target. Only a non-empty, unresolved arg clears it.
    """
    mob = _mob(remember_room)
    victim = _pc(remember_room, "Bob", isolated_registry)

    do_mpremember(mob, "Bob")
    assert mob.mprog_target is victim

    do_mpremember(mob, "   ")

    assert mob.mprog_target is victim


def test_forget_clears_target(remember_room: Room, isolated_registry) -> None:
    """ROM src/mob_cmds.c:1171-1174 — ``mob forget`` sets mprog_target = NULL."""
    mob = _mob(remember_room)
    victim = _pc(remember_room, "Bob", isolated_registry)

    do_mpremember(mob, "Bob")
    assert mob.mprog_target is victim

    do_mpforget(mob, "")

    assert mob.mprog_target is None
