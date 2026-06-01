"""MAGIC-006 — plague room line uses ROM ``$s skin`` + ``$n`` PERS masking.

ROM ``spell_plague`` (``src/magic.c:3921``) broadcasts
``act("$n screams in agony as plague sores erupt from $s skin.", victim, NULL,
NULL, TO_ROOM)``.  ``comm.c`` renders ``$n`` per recipient through
``PERS(victim, to)`` (so an invisible victim masks to "someone") and ``$s`` as
the victim's gendered possessive (his/her/its).

The Python port baked ``_character_name(victim)`` and the literal ``"their
skin"`` into the room broadcast via the module-level ``_act_room`` helper, so it
neither masked an invisible victim (INV-027) nor rendered ROM's gendered
possessive.  The fix routes the line through the shared
``act_to_room("$n ... $s skin.", victim)`` helper.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room() -> Room:
    room = Room(vnum=42840, name="Plague PERS Lab", sector_type=int(Sector.INSIDE))
    room.people = []
    return room


def _pc(name: str, room: Room, *, level: int = 24, sex: Sex | None = None) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False)
    if sex is not None:
        char.sex = sex
    room.add_character(char)
    char.messages = []
    return char


class TestPlaguePronounMasking:
    def test_room_line_renders_gendered_possessive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/magic.c:3921 — $s is the victim's possessive (his/her/its),
        # not the literal "their".
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)
        room = _room()
        caster = _pc("Cleric", room, level=28)
        male = _pc("Garrick", room, sex=Sex.MALE)
        witness = _pc("Observer", room, level=22)

        assert skill_handlers.plague(caster, male) is True

        expected = "Garrick screams in agony as plague sores erupt from his skin."
        assert witness.messages[-1] == expected, f"Expected gendered $s, got: {witness.messages}"

    def test_room_line_renders_female_possessive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)
        room = _room()
        caster = _pc("Cleric", room, level=28)
        female = _pc("Mara", room, sex=Sex.FEMALE)
        witness = _pc("Observer", room, level=22)

        assert skill_handlers.plague(caster, female) is True
        assert witness.messages[-1] == "Mara screams in agony as plague sores erupt from her skin."

    def test_room_line_masks_invisible_victim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM renders $n per recipient through PERS — a witness who cannot see
        # the (invisible) victim sees "Someone" (INV-027).
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)
        room = _room()
        caster = _pc("Cleric", room, level=28)
        victim = _pc("Garrick", room, sex=Sex.MALE)
        victim.add_affect(AffectFlag.INVISIBLE)
        witness = _pc("Observer", room, level=22)

        assert skill_handlers.plague(caster, victim) is True

        msg = witness.messages[-1]
        assert msg == "Someone screams in agony as plague sores erupt from his skin.", (
            f"Invisible victim name leaked (no $n PERS masking): {witness.messages}"
        )
