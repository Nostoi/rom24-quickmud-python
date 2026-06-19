"""FIGHT-036 — dirt-kick blind room line uses ROM ``$s eyes`` + ``$n`` + colour.

ROM ``do_dirt`` (``src/fight.c:2614``) broadcasts
``act("{5$n is blinded by the dirt in $s eyes!{x", victim, NULL, NULL,
TO_ROOM)``.  ``comm.c`` renders ``$n`` per recipient via ``PERS(victim, to)``
(an invisible victim masks to "someone"), ``$s`` as the victim's gendered
possessive (his/her/its), and preserves the ``{5``/``{x`` colour codes.

The Python port baked ``_character_name(victim)`` and the literal "their eyes"
into the room broadcast via the module-level ``_act_room`` helper, dropping the
colour codes — neither masking an invisible victim (INV-027), matching ROM's
gendered possessive, nor colouring the line.  The fix routes the line through
``act_to_room("{5$n ... $s eyes!{x", victim)``.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room() -> Room:
    room = Room(vnum=42850, name="Dirt PERS Lab", sector_type=int(Sector.FIELD))
    room.people = []
    room.light = 1  # never dark — isolate the masking under test from room darkness
    return room


def _pc(name: str, room: Room, *, level: int = 20, sex: Sex | None = None) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.perm_stat = [18, 18, 18, 18, 18]
    char.mod_stat = [0] * len(char.perm_stat)
    char.max_hit = 200
    char.hit = 200
    # INV-050: apply_damage re-checks is_safe (ROM src/fight.c:730), which now
    # faithfully enforces the PC-vs-PC clan PK ladder (:1096-1120). Make every
    # combatant a clan member (same clan, <8 level gap) so the pair is a legal
    # kill — otherwise the backstop blocks the dirt kick before any line renders.
    char.clan = 1
    if sex is not None:
        char.sex = sex
    room.add_character(char)
    char.messages = []
    return char


class TestDirtKickPronounMasking:
    def test_room_line_renders_gendered_possessive_and_colour(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/fight.c:2614 — "{5$n is blinded by the dirt in $s eyes!{x".
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
        monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)
        room = _room()
        kicker = _pc("Scout", room, level=22)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)
        witness = _pc("Observer", room, level=16)

        assert skill_handlers.dirt_kicking(kicker, target=victim)

        # The room blind line is followed by the damage broadcast, so assert
        # presence rather than the last message.
        assert "{5Garrick is blinded by the dirt in his eyes!{x" in witness.messages, (
            f"Expected gendered $s + colour, got: {witness.messages}"
        )

    def test_room_line_renders_female_possessive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
        monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)
        room = _room()
        kicker = _pc("Scout", room, level=22)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Mara", room, level=18, sex=Sex.FEMALE)
        witness = _pc("Observer", room, level=16)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert "{5Mara is blinded by the dirt in her eyes!{x" in witness.messages

    def test_room_line_masks_invisible_victim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM renders $n per recipient through PERS — a witness who cannot see
        # the (invisible) victim sees "Someone" (INV-027).
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
        monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)
        room = _room()
        kicker = _pc("Scout", room, level=22)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)
        victim.add_affect(AffectFlag.INVISIBLE)
        witness = _pc("Observer", room, level=16)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert "{5Someone is blinded by the dirt in his eyes!{x" in witness.messages, (
            f"Invisible victim name leaked (no $n PERS masking): {witness.messages}"
        )
        assert not any("Garrick" in m for m in witness.messages), f"Invisible victim name leaked: {witness.messages}"
