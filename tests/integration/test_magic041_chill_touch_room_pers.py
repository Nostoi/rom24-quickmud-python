"""MAGIC-041 — chill_touch's "turns blue and shivers" room broadcast uses $n PERS.

ROM `spell_chill_touch` (`src/magic.c:1417`):
`act("$n turns blue and shivers.", victim, NULL, NULL, TO_ROOM)` — the actor is the
chilled victim (excluded), so `$n` = PERS(victim) = NPC short_descr, capitalized.
The Python hand-rolled a room loop that baked the keyword `name`.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import chill_touch
from mud.utils import rng_mm


def test_magic041_chill_touch_room_broadcast_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    room = Room(vnum=99215, name="Frost Cavern")
    caster = Character(name="Mage", level=20, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    witness = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: high)

    chill_touch(caster, target=goblin)

    # TO_ROOM (actor=victim, excluded): the witness and the caster both see it; the
    # victim does not.
    assert any("A green goblin turns blue and shivers." in m for m in witness.messages), witness.messages
    assert any("A green goblin turns blue and shivers." in m for m in caster.messages), caster.messages
    assert not any("turns blue and shivers" in m for m in goblin.messages), goblin.messages
