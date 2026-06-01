"""FIGHT-035 — disarm uses ROM's TO_CHAR/TO_VICT/TO_NOTVICT split + colour + PERS.

ROM splits every disarm outcome into three distinct ``act()`` legs, and the
TO_NOTVICT leg excludes **both** the kicker (``ch``) and the victim — so neither
actor receives the third-person bystander line, and a bystander receives it
exactly once.

Fail path (``src/fight.c:3211-3215`` ``do_disarm``):
  * TO_CHAR    ``"{5You fail to disarm $N.{x"``
  * TO_VICT    ``"{5$n tries to disarm you, but fails.{x"``
  * TO_NOTVICT ``"{5$n tries to disarm $N, but fails.{x"``

NOREMOVE path (``src/fight.c:2244-2248`` ``disarm``):
  * TO_CHAR    ``"{5$S weapon won't budge!{x"`` (``$S`` = victim's gendered possessive)
  * TO_VICT    ``"{5$n tries to disarm you, but your weapon won't budge!{x"``
  * TO_NOTVICT ``"{5$n tries to disarm $N, but fails.{x"``

Success path (``src/fight.c:2252-2255`` ``disarm``):
  * TO_VICT    ``"{5$n DISARMS you and sends your weapon flying!{x"`` (note CAPS)
  * TO_CHAR    ``"{5You disarm $N!{x"``
  * TO_NOTVICT ``"{5$n disarms $N!{x"``

The Python port baked both names, dropped the ``{5``/``{x`` colour, lower-cased
"DISARMS", rendered ``$S`` as ``"<name>'s"`` instead of the gendered possessive,
and — the correctness bug — passed the TO_NOTVICT line through ``_act_room`` with
only **one** actor excluded, so the other actor double-received the third-person
room line.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.models import Character
from mud.models.constants import AffectFlag, Position, Sector, Sex, WeaponType, WearLocation
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room() -> Room:
    room = Room(vnum=42870, name="Disarm Lab", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    room.light = 1
    return room


def _pc(name: str, room: Room, *, level: int = 30, sex: Sex | None = None, stats: int = 18) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.perm_stat = [stats] * 5
    char.mod_stat = [0] * 5
    char.max_hit = 200
    char.hit = 200
    char.position = Position.FIGHTING
    if sex is not None:
        char.sex = sex
    room.add_character(char)
    char.messages = []
    return char


def _wield(victim: Character, *, extra_flags: int = 0) -> SimpleNamespace:
    weapon = SimpleNamespace(
        prototype=SimpleNamespace(
            name="longsword", short_descr="a longsword", item_type="weapon",
            value=[int(WeaponType.SWORD), 0, 0, 0], level=20,
        ),
        value=[int(WeaponType.SWORD), 0, 0, 0],
        extra_flags=extra_flags,
        short_descr="a longsword",
        item_type="weapon",
        wear_loc=int(WearLocation.WIELD),
        location=None,
    )
    victim.equipment[int(WearLocation.WIELD)] = weapon
    return weapon


def _caster(room: Room, **kw) -> Character:
    ch = _pc("Duelist", room, **kw)
    ch.skills.update({"disarm": 85, "hand to hand": 70, "sword": 80})
    return ch


class TestDisarmActStructure:
    def test_fail_path_to_notvict_excludes_both_actors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/fight.c:3211-3215 — roll fails (number_percent >= chance).
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 100)
        room = _room()
        caster = _caster(room)
        victim = _pc("Mercenary", room, level=28, sex=Sex.MALE, stats=14)
        bystander = _pc("Onlooker", room, level=20)
        _wield(victim)

        assert skill_handlers.disarm(caster, target=victim) is False

        assert "{5You fail to disarm Mercenary.{x" in caster.messages
        assert "{5Duelist tries to disarm you, but fails.{x" in victim.messages
        # The TO_NOTVICT bystander line reaches the bystander exactly once...
        notvict = "{5Duelist tries to disarm Mercenary, but fails.{x"
        assert bystander.messages.count(notvict) == 1, bystander.messages
        # ...and reaches NEITHER actor (TO_NOTVICT excludes ch AND victim).
        assert notvict not in victim.messages, f"victim double-received TO_NOTVICT: {victim.messages}"
        assert notvict not in caster.messages, f"caster received TO_NOTVICT: {caster.messages}"

    def test_fail_to_vict_masks_invisible_caster(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 100)
        room = _room()
        caster = _caster(room)
        caster.add_affect(AffectFlag.INVISIBLE)
        victim = _pc("Mercenary", room, level=28, sex=Sex.MALE, stats=14)
        _wield(victim)

        assert skill_handlers.disarm(caster, target=victim) is False
        assert "{5Someone tries to disarm you, but fails.{x" in victim.messages, victim.messages
        assert not any("Duelist" in m for m in victim.messages), victim.messages

    def test_success_path_legs_colour_caps_and_exclusion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ROM src/fight.c:2252-2255 — roll succeeds.
        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 0)
        room = _room()
        caster = _caster(room)
        victim = _pc("Mercenary", room, level=28, sex=Sex.MALE, stats=14)
        bystander = _pc("Onlooker", room, level=20)
        _wield(victim)

        assert skill_handlers.disarm(caster, target=victim) is True

        assert "{5Duelist DISARMS you and sends your weapon flying!{x" in victim.messages
        assert "{5You disarm Mercenary!{x" in caster.messages
        notvict = "{5Duelist disarms Mercenary!{x"
        assert bystander.messages.count(notvict) == 1, bystander.messages
        assert notvict not in victim.messages, f"victim double-received TO_NOTVICT: {victim.messages}"

    def test_noremove_path_uses_gendered_possessive_and_excludes_caster(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # ROM src/fight.c:2244-2248 — roll succeeds but weapon is ITEM_NOREMOVE.
        from mud.models.constants import ExtraFlag

        monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 0)
        room = _room()
        caster = _caster(room)
        victim = _pc("Mercenary", room, level=28, sex=Sex.MALE, stats=14)
        bystander = _pc("Onlooker", room, level=20)
        _wield(victim, extra_flags=int(ExtraFlag.NOREMOVE))

        assert skill_handlers.disarm(caster, target=victim) is False

        # $S → victim's gendered possessive (his), capitalized behind the { kludge.
        assert "{5His weapon won't budge!{x" in caster.messages, caster.messages
        assert "{5Duelist tries to disarm you, but your weapon won't budge!{x" in victim.messages
        notvict = "{5Duelist tries to disarm Mercenary, but fails.{x"
        assert bystander.messages.count(notvict) == 1, bystander.messages
        # TO_NOTVICT excludes the caster — caster already got the TO_CHAR budge line.
        assert notvict not in caster.messages, f"caster double-received TO_NOTVICT: {caster.messages}"
