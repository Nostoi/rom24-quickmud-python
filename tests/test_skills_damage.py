from __future__ import annotations

import pytest

from mud.math.c_compat import c_div
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def test_dispel_evil_damages_evil_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Priest", level=30, is_npc=False, alignment=400)
    victim = Character(name="Shade", level=28, is_npc=False, alignment=-500, hit=200)
    room = Room(vnum=4100)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 60)

    damage = skill_handlers.dispel_evil(caster, victim)

    assert damage == 60
    assert victim.hit == 140


def test_demonfire_applies_curse_and_fire_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Warlock", level=32, is_npc=False, alignment=-600)
    victim = Character(name="Paladin", level=28, is_npc=False, alignment=450, hit=150)
    observer = Character(name="Witness", is_npc=False)
    room = Room(vnum=4200)
    for ch in (caster, victim, observer):
        room.add_character(ch)

    dice_values = iter([80])
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: next(dice_values))

    save_results = iter([False, False])

    def fake_saves(level: int, target: Character, damage_type: int) -> bool:
        return next(save_results)

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.demonfire(caster, victim)

    assert damage == 80
    assert victim.hit == 70
    assert victim.has_affect(AffectFlag.CURSE)
    assert victim.has_spell_effect("curse")
    assert caster.alignment == -650
    assert victim.messages[-1] == "You feel unclean."
    assert caster.messages[-1] == "Paladin looks very uncomfortable."
    assert observer.messages[-1] == "Warlock calls forth the demons of Hell upon Paladin!"
    assert caster.messages[0] == "You conjure forth the demons of hell!"
    assert victim.messages[0] == "Warlock has assailed you with the demons of Hell!"
def test_cause_light_deals_level_scaled_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Cleric", level=18, is_npc=False)
    victim = Character(name="Raider", level=14, is_npc=False, hit=120, max_hit=120)
    room = Room(vnum=4050)
    room.add_character(caster)
    room.add_character(victim)
    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 7)

    damage = skill_handlers.cause_light(caster, victim)
    expected = 7 + c_div(18, 3)

    assert damage == expected
    assert victim.hit == 120 - expected
    assert any("your spell" in message.lower() for message in caster.messages)
    assert any("spell" in message.lower() for message in victim.messages)


def test_cause_serious_adds_half_level(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Templar", level=20, is_npc=False)
    victim = Character(name="Brute", level=18, is_npc=True, hit=180, max_hit=180)
    room = Room(vnum=4051)
    room.add_character(caster)
    room.add_character(victim)
    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 14)

    damage = skill_handlers.cause_serious(caster, victim)
    expected = 14 + c_div(20, 2)

    assert damage == expected
    assert victim.hit == 180 - expected
    assert any("your spell" in message.lower() for message in caster.messages)
    assert any("spell" in message.lower() for message in victim.messages)


def test_cause_critical_clamps_low_level_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Novice", level=3, is_npc=False)
    victim = Character(name="Ogre", level=12, is_npc=True, hit=150, max_hit=150)
    room = Room(vnum=4052)
    room.add_character(caster)
    room.add_character(victim)
    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 3)

    damage = skill_handlers.cause_critical(caster, victim)

    assert damage == 0
    assert victim.hit == 150
    assert any("miss" in message.lower() for message in caster.messages)


def test_chain_lightning_arcs_room_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Stormcaller", level=12, is_npc=False, hit=220, max_hit=220)
    first = Character(name="Sentinel", level=10, is_npc=False, hit=180, max_hit=180)
    second = Character(name="Raider", level=9, is_npc=True, hit=170, max_hit=170)
    third = Character(name="Scout", level=8, is_npc=True, hit=160, max_hit=160)
    room = Room(vnum=4205)
    for character in (caster, first, second, third):
        room.add_character(character)
        character.messages.clear()

    dice_values = iter([24, 18, 12])
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: next(dice_values))
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    result = skill_handlers.chain_lightning(caster, first)

    assert result is True
    assert first.hit == 156
    assert second.hit == 152
    assert third.hit == 148
    assert any("lightning bolt leaps" in message.lower() for message in caster.messages)
    assert any("hits you" in message.lower() for message in first.messages)
    assert "The bolt hits you!" in second.messages
    assert "The bolt hits you!" in third.messages


def test_chain_lightning_can_backfire_on_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Invoker", level=8, is_npc=False, hit=200, max_hit=200)
    target = Character(name="Bandit", level=6, is_npc=True, hit=150, max_hit=150)
    room = Room(vnum=4206)
    for character in (caster, target):
        room.add_character(character)
        character.messages.clear()

    dice_values = iter([30, 18])
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: next(dice_values))
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    result = skill_handlers.chain_lightning(caster, target)

    assert result is True
    assert target.hit == 120
    assert caster.hit == 182
    assert any("struck by your own lightning" in message.lower() for message in caster.messages)
    assert any("hits you" in message.lower() for message in target.messages)


def test_earthquake_damages_grounded_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    character_registry.clear()
    try:
        room = Room(vnum=4300)
        caster = Character(name="Geomancer", level=18, is_npc=False, hit=220, max_hit=220)
        grounded = Character(name="Mercenary", level=16, is_npc=True, hit=150, max_hit=150)
        flying = Character(name="Wyvern", level=15, is_npc=True, hit=140, max_hit=140)
        witness = Character(name="Observer", level=10, is_npc=False)
        for ch in (caster, grounded, flying, witness):
            room.add_character(ch)
            ch.messages.clear()

        flying.add_affect(AffectFlag.FLYING)
        character_registry.extend([caster, grounded, flying, witness])

        monkeypatch.setattr(rng_mm, "dice", lambda number, size: 9)

        result = skill_handlers.earthquake(caster)

        assert result is True
        expected_damage = caster.level + 9
        assert grounded.hit == 150 - expected_damage
        assert flying.hit == 140
        assert any(message == "The earth trembles beneath your feet!" for message in caster.messages)
        assert any(
            message == "Geomancer makes the earth tremble and shiver."
            for message in witness.messages
        )
    finally:
        character_registry.clear()


def test_earthquake_sends_area_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    character_registry.clear()
    try:
        area = Area(name="Shuddering Caverns", vnum=50)
        other_area = Area(name="Quiet Keep", vnum=51)
        epicenter = Room(vnum=4400, area=area)
        nearby = Room(vnum=4401, area=area)
        distant = Room(vnum=4402, area=other_area)

        caster = Character(name="Cleric", level=20, is_npc=False, hit=210, max_hit=210)
        ally = Character(name="Squire", level=12, is_npc=False)
        area_listener = Character(name="Villager", level=8, is_npc=False)
        far_listener = Character(name="Hermit", level=10, is_npc=False)

        for ch, room in (
            (caster, epicenter),
            (ally, epicenter),
            (area_listener, nearby),
            (far_listener, distant),
        ):
            room.add_character(ch)
            ch.messages.clear()

        character_registry.extend([caster, ally, area_listener, far_listener])
        monkeypatch.setattr(rng_mm, "dice", lambda number, size: 5)

        skill_handlers.earthquake(caster)

        assert any(message == "The earth trembles and shivers." for message in area_listener.messages)
        assert all(
            message != "The earth trembles and shivers."
            for message in far_listener.messages
        )
    finally:
        character_registry.clear()


def test_fireball_uses_rom_damage_table(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Archmage", level=60, is_npc=False)
    victim = Character(name="Brigand", level=45, is_npc=False, hit=400, max_hit=400)
    room = Room(vnum=4100)
    room.add_character(caster)
    room.add_character(victim)

    def fake_number_range(low: int, high: int) -> int:
        assert low == c_div(130, 2)
        assert high == 130 * 2
        return high

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    damage = skill_handlers.fireball(caster, victim)

    assert damage == 260
    assert victim.hit == 140


def test_fireball_save_halves_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Mage", level=25, is_npc=False)
    victim = Character(name="Raider", level=20, is_npc=False, hit=320, max_hit=320)
    room = Room(vnum=4101)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: 180)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: True)

    damage = skill_handlers.fireball(caster, victim)

    assert damage == c_div(180, 2)
    assert victim.hit == 320 - c_div(180, 2)


def test_flamestrike_rolls_rom_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Cleric", level=28, is_npc=False)
    victim = Character(name="Cultist", level=24, is_npc=False, hit=500, max_hit=500)
    room = Room(vnum=4102)
    room.add_character(caster)
    room.add_character(victim)

    def fake_dice(number: int, size: int) -> int:
        assert number == 6 + c_div(28, 2)
        assert size == 8
        return number * size

    monkeypatch.setattr(rng_mm, "dice", fake_dice)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    damage = skill_handlers.flamestrike(caster, victim)

    expected = (6 + c_div(28, 2)) * 8
    assert damage == expected
    assert victim.hit == 500 - expected


def test_flamestrike_save_halves_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Priest", level=20, is_npc=False)
    victim = Character(name="Ghoul", level=18, is_npc=True, hit=260, max_hit=260)
    room = Room(vnum=4103)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 96)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: True)

    damage = skill_handlers.flamestrike(caster, victim)

    assert damage == c_div(96, 2)
    assert victim.hit == 260 - c_div(96, 2)

