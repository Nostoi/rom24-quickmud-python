"""MAGIC-028 — plague "seems to be unaffected" line uses $N PERS (cap).

ROM `spell_plague` (`src/magic.c:3905`): when the victim saves (or is an undead
NPC) and is not the caster, `act("$N seems to be unaffected.", ch, NULL, victim,
TO_CHAR)` — `$N` = PERS(victim) = NPC short_descr, capitalized. The Python baked
`_character_name(victim)`. (The self-cast leg's literal "You feel momentarily ill,
but it passes." was already correct.) Last member of the MAGIC-022 batch.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ActFlag, Position
from mud.models.room import Room
from mud.skills.handlers import plague


def test_magic028_plague_undead_npc_unaffected_uses_pers_shortdescr():
    room = Room(vnum=99198, name="Crypt")
    caster = Character(name="Priest", level=30, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []

    # An undead NPC always takes the save/immune branch (ROM ACT_UNDEAD short-circuit).
    goblin = Character(
        name="goblin",
        is_npc=True,
        short_descr="a green goblin",
        act=int(ActFlag.UNDEAD),
        position=int(Position.STANDING),
    )
    room.add_character(goblin)
    goblin.messages = []

    assert plague(caster, target=goblin) is False
    assert any("A green goblin seems to be unaffected." in m for m in caster.messages), caster.messages
