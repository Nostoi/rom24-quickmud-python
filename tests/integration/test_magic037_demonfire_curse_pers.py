"""MAGIC-037 — demonfire's curse-tail "looks very uncomfortable" uses $N PERS (cap).

ROM `spell_demonfire` (`src/magic.c`) ends with
`spell_curse(gsn_curse, 3*level/4, ch, victim, TARGET_CHAR)`, whose cross-target
line is `act("$N looks very uncomfortable.", ch, NULL, victim, TO_CHAR)` (`:1801`)
— `$N` = PERS(victim) = NPC short_descr, capitalized. The Python's inline copy of
the curse messaging baked the keyword `name`. (The "demons of Hell" TO_ROOM/TO_VICT
lines are a separate gap.)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import demonfire


def test_magic037_demonfire_curse_tail_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    room = Room(vnum=99211, name="Pit")
    # Caster must be evil so demonfire does not redirect victim -> caster.
    caster = Character(
        name="Warlock", level=40, ch_class=0, is_npc=False, alignment=-1000, position=int(Position.STANDING)
    )
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []

    # saves_spell False -> the curse tail applies (and damage is not halved).
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)

    demonfire(caster, target=goblin)
    assert any("A green goblin looks very uncomfortable." in m for m in caster.messages), caster.messages
