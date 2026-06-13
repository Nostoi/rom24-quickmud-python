"""MAGIC-040 — cure_blindness/cure_poison room broadcasts use $n PERS (actor=victim).

ROM (`src/magic.c`, both `act("$n …", victim, NULL, NULL, TO_ROOM)` — the ACTOR is
the cured victim, who is excluded):
  - `spell_cure_blindness` `:1062` "$n is no longer blinded."
  - `spell_cure_poison`    `:1702` "$n looks much better."

`$n` = PERS(victim), capitalized at buf[0]. The Python hand-rolled a room loop that
baked the keyword `name`, so a bystander saw lowercase "goblin is no longer
blinded." vs ROM "A green goblin …".
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import cure_blindness, cure_poison


def _setup(flag: AffectFlag) -> tuple[Character, Character, Character]:
    room = Room(vnum=99214, name="Infirmary")
    caster = Character(name="Healer", level=40, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.affected_by |= int(flag)
    witness = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []
    return caster, goblin, witness


def test_magic040_cure_blindness_room_broadcast_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    caster, goblin, witness = _setup(AffectFlag.BLIND)
    monkeypatch.setattr(skill_handlers, "check_dispel", lambda *a, **k: True)

    assert cure_blindness(caster, target=goblin) is True
    assert any("A green goblin is no longer blinded." in m for m in witness.messages), witness.messages


def test_magic040_cure_poison_room_broadcast_uses_pers_cap(monkeypatch: pytest.MonkeyPatch):
    caster, goblin, witness = _setup(AffectFlag.POISON)
    monkeypatch.setattr(skill_handlers, "check_dispel", lambda *a, **k: True)

    assert cure_poison(caster, target=goblin) is True
    assert any("A green goblin looks much better." in m for m in witness.messages), witness.messages
