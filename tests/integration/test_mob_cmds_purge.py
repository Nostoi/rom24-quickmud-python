"""Integration tests for ``do_mppurge`` (MOBprog ``purge`` script command).

ROM C reference: ``src/mob_cmds.c:623-677`` — ROM treats *empty arg* as
purge-all (every NPC except self + non-NOPURGE objects in the room) and has
no special ``"all"`` keyword. A literal ``mob purge all`` falls into the
named-target path, which fails to find an NPC or object named "all", logs
``bug("Mppurge - Bad argument from vnum %d.", ...)`` and returns.

Closes MOBCMD-007.
"""

from __future__ import annotations

import logging

import pytest

from mud.mob_cmds import do_mppurge
from mud.models.character import Character, character_registry
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _reset_registry():
    character_registry.clear()
    yield
    character_registry.clear()


@pytest.fixture
def purge_room() -> Room:
    return Room(vnum=9920, name="Purge Test Room")


@pytest.fixture
def controller(purge_room: Room) -> Character:
    mob = Character(name="Controller", is_npc=True)
    purge_room.add_character(mob)
    character_registry.append(mob)
    return mob


@pytest.fixture
def ally(purge_room: Room) -> Character:
    # Name deliberately avoids any prefix overlap with "all" so ROM's
    # `get_char_room` (and Python's `_find_char_in_room`) does not match it
    # against the literal token "all".
    other = Character(name="Bystander", is_npc=True)
    purge_room.add_character(other)
    character_registry.append(other)
    return other


class TestMpPurgeNoLiteralAllKeyword:
    """MOBCMD-007: ROM has no ``"all"`` keyword for ``mob purge``. The
    literal token ``all`` is treated as a name; if no NPC or object in
    the room is named ``"all"``, ROM logs a bug and returns without
    purging anything (``src/mob_cmds.c:655-665``)."""

    def test_literal_all_does_not_purge_room(self, controller, ally, caplog):
        with caplog.at_level(logging.WARNING, logger="mud.mob_cmds"):
            do_mppurge(controller, "all")

        # ROM: nothing in the room is named "all", so no NPC/object purged.
        assert ally in controller.room.people, (
            "do_mppurge('all') purged room NPCs; ROM has no 'all' keyword"
            " (see src/mob_cmds.c:655-665) — the token must be treated as"
            " a name, not a wildcard."
        )
        assert any(
            "Mppurge" in record.message and "Bad argument" in record.message
            for record in caplog.records
        ), (
            "expected an Mppurge bug log when the named target cannot be"
            f" resolved; got {[r.message for r in caplog.records]!r}."
        )

    def test_empty_arg_still_purges_room(self, controller, ally):
        # Positive control: ROM's no-arg form (`mob purge`) clears NPCs.
        do_mppurge(controller, "")

        assert ally not in controller.room.people, (
            "do_mppurge('') with empty arg must purge non-NOPURGE NPCs"
            " (ROM src/mob_cmds.c:631-652)."
        )
        assert controller in controller.room.people, "self never purged"
