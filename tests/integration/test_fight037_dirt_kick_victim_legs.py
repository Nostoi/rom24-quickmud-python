"""FIGHT-037 — dirt-kick victim legs: ``$n`` PERS + ``{5..{x`` colour, no invented caster line.

ROM ``do_dirt`` success branch (``src/fight.c:2611-2631``) emits exactly three
visible lines on a hit:

  * ``:2614`` TO_ROOM  — ``"{5$n is blinded by the dirt in $s eyes!{x"`` (victim
    subject; reaches the kicker too — handled by FIGHT-036's ``act_to_room``,
    which excludes only the victim).
  * ``:2616`` TO_VICT  — ``"{5$n kicks dirt in your eyes!{x"`` (kicker subject,
    rendered per the victim via ``PERS(ch, victim)`` — an invisible kicker masks
    to "someone" — wrapped in the ``{5``/``{x`` colour codes).
  * ``:2618`` send_to_char — ``"{5You can't see a thing!{x"`` to the victim.

The success branch sends the **kicker NO self message** — the kicker only sees
the ``:2614`` blind line as a room recipient.

The Python port (1) baked the kicker name and dropped the colour on the TO_VICT
leg, (2) dropped the colour on the victim self-line, and (3) **invented** a
``"You kick dirt in <victim>'s eyes!"`` caster line ROM never emits.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room() -> Room:
    room = Room(vnum=42851, name="Dirt Victim Lab", sector_type=int(Sector.FIELD))
    room.people = []
    room.light = 1  # never dark — isolate the masking under test from room darkness
    return room


def _pc(name: str, room: Room, *, level: int = 20, sex: Sex | None = None) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.perm_stat = [18, 18, 18, 18, 18]
    char.mod_stat = [0] * len(char.perm_stat)
    char.max_hit = 200
    char.hit = 200
    if sex is not None:
        char.sex = sex
    room.add_character(char)
    char.messages = []
    return char


def _hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)


class TestDirtKickVictimLegs:
    def test_victim_to_vict_line_has_pers_and_colour(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/fight.c:2616 — "{5$n kicks dirt in your eyes!{x", ch, TO_VICT.
        _hit(monkeypatch)
        room = _room()
        kicker = _pc("Scout", room, level=22, sex=Sex.MALE)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert "{5Scout kicks dirt in your eyes!{x" in victim.messages, (
            f"Expected $n PERS + colour TO_VICT line, got: {victim.messages}"
        )

    def test_victim_self_line_has_colour(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/fight.c:2618 — send_to_char("{5You can't see a thing!{x\n\r", victim).
        _hit(monkeypatch)
        room = _room()
        kicker = _pc("Scout", room, level=22)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert "{5You can't see a thing!{x" in victim.messages, (
            f"Expected coloured victim self-line, got: {victim.messages}"
        )

    def test_to_vict_masks_invisible_kicker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM renders $n per recipient via PERS — a victim who cannot see the
        # invisible kicker sees "Someone" (INV-027).
        _hit(monkeypatch)
        room = _room()
        kicker = _pc("Scout", room, level=22, sex=Sex.MALE)
        kicker.skills["dirt kicking"] = 75
        kicker.add_affect(AffectFlag.INVISIBLE)
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert "{5Someone kicks dirt in your eyes!{x" in victim.messages, (
            f"Invisible kicker name leaked (no $n PERS masking): {victim.messages}"
        )
        assert not any("Scout" in m for m in victim.messages), (
            f"Invisible kicker name leaked: {victim.messages}"
        )

    def test_kicker_gets_no_invented_self_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM's success branch sends the kicker NO self message — only the
        # :2614 blind line reaches them as a room recipient.
        _hit(monkeypatch)
        room = _room()
        kicker = _pc("Scout", room, level=22)
        kicker.skills["dirt kicking"] = 75
        victim = _pc("Garrick", room, level=18, sex=Sex.MALE)

        assert skill_handlers.dirt_kicking(kicker, target=victim)
        assert not any("You kick dirt" in m for m in kicker.messages), (
            f"Python invented a caster self-line ROM never emits: {kicker.messages}"
        )
        # The kicker still sees the :2614 blind line as a room recipient.
        assert "{5Garrick is blinded by the dirt in his eyes!{x" in kicker.messages, (
            f"Kicker should receive the room blind line: {kicker.messages}"
        )
