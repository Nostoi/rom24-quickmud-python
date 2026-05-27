"""BCAST-025 — ``do_surrender`` must emit TO_VICT and TO_NOTVICT broadcasts.

ROM contract (``src/fight.c:3230-3232``)::

    act ("You surrender to $N!", ch, NULL, mob, TO_CHAR);
    act ("$n surrenders to you!", ch, NULL, mob, TO_VICT);
    act ("$n tries to surrender to $N!", ch, NULL, mob, TO_NOTVICT);

Python pre-fix only returned the TO_CHAR string. The opponent and any
bystanders received no message — they had no idea the surrender
happened. Audit: BROADCAST_COVERAGE.md row 25, ROM=2 non-TO_CHAR
acts, Python pre-fix=0.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_surrender
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_surrender_sends_to_vict_and_notvict() -> None:
    """do_surrender must broadcast to the opponent and to bystanders.

    ROM src/fight.c:3231 → TO_VICT "$n surrenders to you!"
    ROM src/fight.c:3232 → TO_NOTVICT "$n tries to surrender to $N!"
    """
    room = Room(vnum=99963, name="Surrender probe")
    char = Character(name="Coward", is_npc=False, position=Position.FIGHTING)
    char.level = 10
    char.messages = []

    opponent = Character(name="Brute", is_npc=False, position=Position.FIGHTING)
    opponent.level = 10
    opponent.messages = []

    bystander = Character(name="Witness", is_npc=False, position=Position.STANDING)
    bystander.level = 10
    bystander.messages = []

    room.add_character(char)
    room.add_character(opponent)
    room.add_character(bystander)
    character_registry.extend([char, opponent, bystander])

    char.fighting = opponent
    opponent.fighting = char

    do_surrender(char, "")

    opponent_msgs = " ".join(opponent.messages)
    assert "surrenders to you" in opponent_msgs, (
        "ROM src/fight.c:3231 calls act(..., TO_VICT). Opponent must "
        f"see the surrender message. Got: {opponent.messages!r}"
    )

    bystander_msgs = " ".join(bystander.messages)
    assert "tries to surrender" in bystander_msgs, (
        "ROM src/fight.c:3232 calls act(..., TO_NOTVICT). Other room "
        f"people must see the surrender attempt. Got: {bystander.messages!r}"
    )
