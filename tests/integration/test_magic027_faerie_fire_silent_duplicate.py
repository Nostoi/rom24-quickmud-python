"""MAGIC-027 — faerie_fire on an already-affected victim is SILENT (ROM parity).

ROM `spell_faerie_fire` (`src/magic.c:2811-2812`):

    if (IS_AFFECTED (victim, AFF_FAERIE_FIRE))
        return;

— a bare `return` with NO message. The Python `faerie_fire` handler invented two
non-ROM lines ("You are already surrounded by a pink outline." / "$N is already
surrounded by a pink outline."). ROM sends nothing; we replicate exactly.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import faerie_fire


def _setup(self_cast: bool) -> tuple[Character, Character]:
    room = Room(vnum=99197, name="Arena")
    caster = Character(name="Illusionist", level=18, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    if self_cast:
        return caster, caster
    target = Character(name="Rogue", level=16, is_npc=False, position=int(Position.STANDING))
    room.add_character(target)
    target.messages = []
    return caster, target


def test_magic027_faerie_fire_duplicate_cross_target_is_silent():
    caster, target = _setup(self_cast=False)
    assert faerie_fire(caster, target) is True
    caster.messages.clear()
    target.messages.clear()

    assert faerie_fire(caster, target) is False
    # ROM emits NOTHING on the duplicate.
    assert caster.messages == [], caster.messages
    assert not any("already surrounded" in m for m in target.messages), target.messages


def test_magic027_faerie_fire_duplicate_self_cast_is_silent():
    caster, target = _setup(self_cast=True)
    assert faerie_fire(caster, target) is True
    caster.messages.clear()

    assert faerie_fire(caster, target) is False
    assert caster.messages == [], caster.messages
