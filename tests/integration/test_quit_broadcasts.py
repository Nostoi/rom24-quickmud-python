"""BCAST-018 — ``do_quit`` must emit the ROM TO_ROOM broadcast.

ROM contract (``src/act_comm.c:1462-1518``):

- Line 1482: ``act("$n has left the game.", ch, NULL, NULL, TO_ROOM)``
  fires AFTER the actor's "Alas, all good things…" line and BEFORE
  ``extract_char`` (line 1499). The actor is still in the room at
  broadcast time, so witnesses see the message in their current room.

ROM also early-returns for NPCs (line 1467-1468) and refuses when
fighting or below STUNNED (lines 1470-1480). Python's `do_quit`
mirrors the position guards but currently emits no room broadcast at
all — the witness sees nothing.

Audit row: ``docs/parity/audits/BROADCAST_COVERAGE.md`` row 18 — R=1
non-TO_CHAR act vs Py=0.
"""

from __future__ import annotations

import pytest

from mud.commands.session import do_quit
from mud.models.character import Character, PCData
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def quit_room_setup(monkeypatch):
    # Stub out save_character so the test isn't doing real I/O.
    import mud.account.account_manager as am

    monkeypatch.setattr(am, "save_character", lambda ch: None)

    room = Room(vnum=99821, name="Quit Probe Room")
    room.people = []
    room.contents = []
    room.exits = [None] * 6
    room_registry[99821] = room

    actor = Character(name="Departer", level=10, room=room, is_npc=False, position=Position.STANDING)
    actor.pcdata = PCData()
    actor.messages = []
    room.people.append(actor)

    witness = Character(name="Onlooker", level=10, room=room, is_npc=False, position=Position.STANDING)
    witness.pcdata = PCData()
    witness.messages = []
    room.people.append(witness)

    yield actor, witness, room

    room_registry.pop(99821, None)


def test_quit_broadcasts_to_room(quit_room_setup):
    """ROM src/act_comm.c:1482 — act("$n has left the game.", ch, NULL, NULL, TO_ROOM)."""
    actor, witness, _room = quit_room_setup

    result = do_quit(actor, "")

    assert "May your travels be safe." in result
    assert "Departer has left the game." in witness.messages, (
        f"Witness should see '$n has left the game.'; got {witness.messages!r}"
    )
    assert not any("has left the game" in m for m in actor.messages), (
        "Actor must be excluded from the TO_ROOM broadcast — ROM uses TO_ROOM, not TO_ALL"
    )


def test_quit_while_fighting_does_not_broadcast(quit_room_setup):
    """ROM src/act_comm.c:1470-1474 — fighting blocks quit; no broadcast emitted."""
    actor, witness, _room = quit_room_setup
    actor.position = Position.FIGHTING

    result = do_quit(actor, "")

    assert "No way!" in result
    assert not any("has left" in m for m in witness.messages), (
        f"Blocked quit must not broadcast; got {witness.messages!r}"
    )


def test_quit_below_stunned_does_not_broadcast(quit_room_setup):
    """ROM src/act_comm.c:1476-1480 — position < STUNNED blocks quit; no broadcast."""
    actor, witness, _room = quit_room_setup
    actor.position = Position.DEAD  # below STUNNED

    result = do_quit(actor, "")

    assert "DEAD" in result
    assert not any("has left" in m for m in witness.messages)
