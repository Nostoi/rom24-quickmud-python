"""SLAY-002 — ``do_slay`` must emit TO_VICT and TO_NOTVICT broadcasts.

ROM contract (``src/fight.c:3282-3284``)::

    act ("{1You slay $M in cold blood!{x", ch, NULL, victim, TO_CHAR);
    act ("{1$n slays you in cold blood!{x", ch, NULL, victim, TO_VICT);
    act ("{1$n slays $N in cold blood!{x", ch, NULL, victim, TO_NOTVICT);
    raw_kill (victim);

Python pre-fix only returned the TO_CHAR string. The victim and any
bystanders received no message — divergent from ROM. Since ``raw_kill``
removes the victim from the room, the broadcasts must fire before the
kill.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_load import do_slay
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


def test_slay_sends_to_vict_and_notvict() -> None:
    """``do_slay`` must broadcast to the victim and to other room people.

    ROM ``src/fight.c:3283`` → TO_VICT "$n slays you in cold blood!".
    ROM ``src/fight.c:3284`` → TO_NOTVICT "$n slays $N in cold blood!".
    """
    room = Room(vnum=99962, name="Slay broadcast probe")
    immortal = Character(name="Immortal", is_npc=False, position=Position.STANDING)
    immortal.level = 60
    immortal.trust = 60
    immortal.messages = []

    npc = Character(name="Victim", is_npc=True, position=Position.STANDING)
    npc.short_descr = "the test mob"
    npc.level = 1
    npc.hit = 100
    npc.max_hit = 100
    npc.messages = []

    bystander = Character(name="Bystander", is_npc=False, position=Position.STANDING)
    bystander.level = 10
    bystander.messages = []

    room.add_character(immortal)
    room.add_character(npc)
    room.add_character(bystander)
    character_registry.extend([immortal, npc, bystander])

    do_slay(immortal, "Victim")

    vict_messages = " ".join(npc.messages)
    assert "slays you in cold blood" in vict_messages, (
        f"ROM src/fight.c:3283 calls act(..., TO_VICT). Victim must see the slay message. Got: {npc.messages!r}"
    )

    bystander_messages = " ".join(bystander.messages)
    assert "slays" in bystander_messages and "in cold blood" in bystander_messages, (
        "ROM src/fight.c:3284 calls act(..., TO_NOTVICT). Other room "
        f"people must see the slay message. Got: {bystander.messages!r}"
    )
    assert "you" not in bystander_messages.lower().split("slays")[1].split("in cold blood")[0], (
        "TO_NOTVICT must use third-person ($N), not second-person."
    )
