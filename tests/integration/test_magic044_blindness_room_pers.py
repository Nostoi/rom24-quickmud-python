"""MAGIC-044 — blindness's "appears to be blinded" room broadcast uses $n PERS.

ROM `spell_blindness` (`src/magic.c:889`): `act("$n appears to be blinded.",
victim, NULL, NULL, TO_ROOM)` — the actor is the blinded victim (excluded), so
`$n` = PERS(victim) = NPC short_descr, capitalized. The Python hand-rolled a room
loop that baked `target.name`.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import blindness


def test_magic044_blindness_room_broadcast_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    room = Room(vnum=99218, name="Dark Hall")
    caster = Character(name="Mage", level=40, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    witness = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)

    assert blindness(caster, target=goblin) is True
    # TO_ROOM (actor=victim, excluded): witness + caster see the PERS line; victim does not.
    assert any("A green goblin appears to be blinded." in m for m in witness.messages), witness.messages
    assert not any("appears to be blinded" in m for m in goblin.messages), goblin.messages
