"""MAGIC-032 — sanctuary cross-target reject line uses $N PERS (cap).

ROM `spell_sanctuary` (`src/magic.c:4284`): when the victim already has
AFF_SANCTUARY and is not the caster, `act("$N is already in sanctuary.", ch, NULL,
victim, TO_CHAR)` — `$N` = PERS(victim) = NPC short_descr, capitalized. The
self-cast leg ("You are already in sanctuary.", `:4282`) is a ROM literal and was
already correct. The Python baked `target.name`.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import sanctuary


def test_magic032_sanctuary_already_affected_npc_uses_pers_cap():
    room = Room(vnum=99204, name="Shrine")
    caster = Character(name="Cleric", level=30, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []

    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    goblin.affected_by |= int(AffectFlag.SANCTUARY)

    assert sanctuary(caster, goblin) is False
    assert any("A green goblin is already in sanctuary." in m for m in caster.messages), caster.messages
