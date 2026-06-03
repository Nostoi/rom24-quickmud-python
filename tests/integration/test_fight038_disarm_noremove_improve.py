"""FIGHT-038 — a NOREMOVE ("won't budge") disarm credits skill improvement TRUE.

ROM ``do_disarm`` (``src/fight.c:3202-3217``) only enters the success branch on a
made roll (``number_percent() < chance``); that branch calls ``disarm(ch, victim)``
and then, unconditionally, ``check_improve(ch, gsn_disarm, TRUE, 1)`` (``:3206``).
The NOREMOVE "won't budge" case lives inside ``disarm()`` (``src/fight.c:2242-2249``)
— it emits the budge messages and ``return``s, so control falls back to ``:3206``
and the disarm is still credited as a skill *success* for improvement.

The Python port's NOREMOVE early-return called ``check_improve(caster, "disarm",
False, 1)`` — crediting a failure. This test pins ROM's TRUE.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.models import Character
from mud.models.constants import ExtraFlag, Position, Sector, Sex, WeaponType, WearLocation
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room() -> Room:
    room = Room(vnum=42871, name="Disarm Improve Lab", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    room.light = 1
    return room


def _pc(name: str, room: Room, *, level: int = 30, stats: int = 18) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.perm_stat = [stats] * 5
    char.mod_stat = [0] * 5
    char.max_hit = 200
    char.hit = 200
    char.position = Position.FIGHTING
    room.add_character(char)
    char.messages = []
    return char


def _wield_noremove(victim: Character) -> SimpleNamespace:
    weapon = SimpleNamespace(
        prototype=SimpleNamespace(
            name="cursed blade",
            short_descr="a cursed blade",
            item_type="weapon",
            value=[int(WeaponType.SWORD), 0, 0, 0],
            level=20,
        ),
        value=[int(WeaponType.SWORD), 0, 0, 0],
        extra_flags=int(ExtraFlag.NOREMOVE),
        short_descr="a cursed blade",
        item_type="weapon",
        wear_loc=int(WearLocation.WIELD),
        location=None,
    )
    victim.equipment[int(WearLocation.WIELD)] = weapon
    return weapon


def test_noremove_disarm_credits_improve_true(monkeypatch: pytest.MonkeyPatch) -> None:
    # ROM src/fight.c:3206 — successful roll → check_improve(..., TRUE, 1) even
    # when disarm() bails on a NOREMOVE weapon.
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 0)

    recorded: list[tuple[bool, int]] = []

    def _record(ch: Character, name: str, success: bool, multiplier: int) -> None:
        recorded.append((success, multiplier))

    monkeypatch.setattr(skill_handlers, "check_improve", _record)

    room = _room()
    caster = _pc("Duelist", room)
    caster.skills.update({"disarm": 85, "hand to hand": 70, "sword": 80})
    victim = _pc("Mercenary", room, level=28, stats=14)
    victim.sex = Sex.MALE
    _wield_noremove(victim)

    assert skill_handlers.disarm(caster, target=victim) is False
    assert recorded == [(True, 1)], f"NOREMOVE disarm should credit skill improvement TRUE (ROM :3206), got: {recorded}"
