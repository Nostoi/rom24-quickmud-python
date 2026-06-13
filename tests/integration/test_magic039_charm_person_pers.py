"""MAGIC-039 — charm_person's two messages use PERS ($n TO_VICT, $N TO_CHAR).

ROM `spell_charm_person` (`src/magic.c:1388-1390`):
  - `act("Isn't $n just so nice?", ch, NULL, victim, TO_VICT)` — `$n` = PERS(caster)
  - `act("$N looks at you with adoring eyes.", ch, NULL, victim, TO_CHAR)` — `$N`
    = PERS(victim), capitalized

The Python baked `actor_name` / `target_name`.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import charm_person


def test_magic039_charm_person_messages_use_pers(monkeypatch: pytest.MonkeyPatch):
    room = Room(vnum=99213, name="Grove")
    caster = Character(name="Mage", level=40, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", level=10, position=int(Position.STANDING)
    )
    room.add_character(goblin)
    goblin.messages = []

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)

    assert charm_person(caster, target=goblin) is True
    # TO_VICT: $n = PERS(caster) seen by the victim.
    assert any("Isn't Mage just so nice?" in m for m in goblin.messages), goblin.messages
    # TO_CHAR: $N = PERS(victim), capitalized.
    assert any("A green goblin looks at you with adoring eyes." in m for m in caster.messages), caster.messages
