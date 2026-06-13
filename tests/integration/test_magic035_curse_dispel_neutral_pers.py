"""MAGIC-035 — curse / dispel_evil / dispel_good TO_CHAR lines use $N PERS (cap).

ROM (`src/magic.c`, all `act("$N …", ch, NULL, victim, TO_CHAR)`):
  - `spell_curse`       `:1801` "$N looks very uncomfortable." (cross-target only)
  - `spell_dispel_evil` `:2027` "$N does not seem to be affected." (neutral victim)
  - `spell_dispel_good` `:2059` "$N does not seem to be affected." (neutral victim)

`$N` = PERS(victim) = NPC short_descr, capitalized. The Python baked the keyword
`name`. (The is_good/is_evil TO_ROOM branches — "Mota protects $N." / "$N is
protected by $S evil." — are a separate gap.)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import curse, dispel_evil, dispel_good


def _setup() -> tuple[Character, Character, Room]:
    room = Room(vnum=99209, name="Arena")
    caster = Character(name="Mage", level=40, ch_class=0, is_npc=False, alignment=0, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", alignment=0, position=int(Position.STANDING)
    )
    room.add_character(goblin)
    goblin.messages = []
    return caster, goblin, room


def test_magic035_curse_cross_target_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    caster, goblin, _ = _setup()
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)

    assert curse(caster, target=goblin) is True
    assert any("A green goblin looks very uncomfortable." in m for m in caster.messages), caster.messages


def test_magic035_dispel_evil_neutral_uses_pers_cap():
    caster, goblin, _ = _setup()
    assert dispel_evil(caster, target=goblin) == 0
    assert any("A green goblin does not seem to be affected." in m for m in caster.messages), caster.messages


def test_magic035_dispel_good_neutral_uses_pers_cap():
    caster, goblin, _ = _setup()
    assert dispel_good(caster, target=goblin) == 0
    assert any("A green goblin does not seem to be affected." in m for m in caster.messages), caster.messages
