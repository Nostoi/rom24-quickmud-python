"""MAGIC-042 — faerie_fog's "$n is revealed!" broadcast uses per-recipient PERS.

ROM `spell_faerie_fog` (`src/magic.c:2850`): for each revealed character,
`act("$n is revealed!", ich, NULL, NULL, TO_ROOM)` — the actor is the revealed
char (excluded), so `$n` = PERS(ich) = NPC short_descr, capitalized. The Python
passed a pre-baked `f"{_character_name(occupant)} is revealed!"` string to
`_act_room`, so it never did per-recipient PERS (NPC short_descr / masking).
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import faerie_fog


def test_magic042_faerie_fog_revealed_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    room = Room(vnum=99216, name="Misty Hollow")
    caster = Character(name="Mage", level=40, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    goblin.affected_by |= int(AffectFlag.HIDE)
    room.add_character(goblin)
    goblin.messages = []
    witness = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []

    # Only the goblin fails the save (gets revealed); the witness saves out.
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: victim is not goblin)

    assert faerie_fog(caster) is True
    # TO_ROOM (actor=revealed goblin, excluded): the witness sees the PERS line.
    assert any("A green goblin is revealed!" in m for m in witness.messages), witness.messages
    assert not any("is revealed!" in m for m in goblin.messages if "A green goblin" in m), goblin.messages
