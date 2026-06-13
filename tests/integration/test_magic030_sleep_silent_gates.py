"""MAGIC-030 — spell_sleep is SILENT on its reject gates (ROM parity).

ROM `spell_sleep` (`src/magic.c:4363-4366`):

    if (IS_AFFECTED (victim, AFF_SLEEP)
        || (IS_NPC (victim) && IS_SET (victim->act, ACT_UNDEAD))
        || (level + 2) < victim->level
        || saves_spell (level - 4, victim, DAM_CHARM)) return;

— a bare `return` with NO message on any gate. The Python invented "You are
already fast asleep." / "$N is already fast asleep." / "$N is immune to sleep."
ROM sends nothing; we replicate exactly. (Same spurious-output class as MAGIC-027.)
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import sleep


def _caster(room: Room) -> Character:
    c = Character(name="Mage", level=40, ch_class=0, is_npc=False, position=int(Position.STANDING))
    room.add_character(c)
    c.messages = []
    return c


def test_magic030_sleep_already_affected_is_silent():
    room = Room(vnum=99199, name="Hall")
    caster = _caster(room)
    target = Character(name="Rogue", level=20, is_npc=False, position=int(Position.STANDING))
    room.add_character(target)
    target.messages = []
    target.affected_by |= int(AffectFlag.SLEEP)

    assert sleep(caster, target=target) is False
    assert caster.messages == [], caster.messages


def test_magic030_sleep_undead_npc_is_silent():
    room = Room(vnum=99200, name="Crypt")
    caster = _caster(room)
    ghoul = Character(
        name="ghoul",
        is_npc=True,
        short_descr="a rotting ghoul",
        act=int(ActFlag.UNDEAD),
        level=20,
        position=int(Position.STANDING),
    )
    room.add_character(ghoul)
    ghoul.messages = []

    assert sleep(caster, target=ghoul) is False
    assert caster.messages == [], caster.messages


def test_magic030_sleep_self_already_asleep_is_silent():
    room = Room(vnum=99201, name="Hall")
    caster = _caster(room)
    caster.affected_by |= int(AffectFlag.SLEEP)

    assert sleep(caster, target=caster) is False
    assert caster.messages == [], caster.messages
