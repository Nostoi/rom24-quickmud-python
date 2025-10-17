from __future__ import annotations

import pytest

from mud.advancement import exp_per_level
from mud.math.c_compat import c_div
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, DamageType, ItemType
from mud.models.obj import ObjectData
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


def test_ray_of_truth_blinds_and_scales_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Templar", level=40, is_npc=False, alignment=700)
    victim = Character(name="Shade", level=38, is_npc=True, alignment=0, hit=200, max_hit=200)
    room = Room(vnum=5300)
    room.add_character(caster)
    room.add_character(victim)
    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 100)

    saves_calls: list[tuple[int, Character, DamageType]] = []

    def fake_saves(level: int, target: Character, dtype: DamageType) -> bool:
        saves_calls.append((level, target, dtype))
        return False

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.ray_of_truth(caster, victim)

    assert damage == 12
    assert victim.hit == 188
    assert victim.has_affect(AffectFlag.BLIND)
    assert victim.has_spell_effect("blindness")
    assert len(saves_calls) == 2
    assert saves_calls[0][2] is DamageType.HOLY
    assert saves_calls[1][2] == int(DamageType.OTHER)
    assert any("blinding ray of light" in message for message in caster.messages)
    assert victim.messages[-1] == "You are blinded!"


def test_ray_of_truth_respects_good_and_evil_alignment(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Crusader", level=42, is_npc=False, alignment=650)
    good_target = Character(name="Saint", level=40, is_npc=False, alignment=900, hit=220, max_hit=220)
    room = Room(vnum=5301)
    room.add_character(caster)
    room.add_character(good_target)
    caster.messages.clear()
    good_target.messages.clear()

    saves_called: list[tuple[int, Character, DamageType]] = []

    def no_saves(level: int, target: Character, dtype: DamageType) -> bool:
        saves_called.append((level, target, dtype))
        return False

    monkeypatch.setattr(skill_handlers, "saves_spell", no_saves)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 90)

    damage = skill_handlers.ray_of_truth(caster, good_target)

    assert damage == 0
    assert good_target.hit == 220
    assert saves_called == []
    assert "powerless" in good_target.messages[-1]

    evil_caster = Character(name="Blackguard", level=42, is_npc=False, alignment=-700, hit=210, max_hit=210)
    victim = Character(name="Witness", level=35, is_npc=True, alignment=-200, hit=190, max_hit=190)
    room.add_character(evil_caster)
    room.add_character(victim)
    evil_caster.messages.clear()
    victim.messages.clear()

    saves_results = iter([False, False])

    def sequenced_saves(level: int, target: Character, dtype: DamageType) -> bool:
        return next(saves_results)

    monkeypatch.setattr(skill_handlers, "saves_spell", sequenced_saves)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 80)

    recoil = skill_handlers.ray_of_truth(evil_caster, victim)

    assert recoil == 82
    assert evil_caster.hit == 128
    assert victim.hit == 190
    assert evil_caster.has_affect(AffectFlag.BLIND)
    assert "explodes inside you" in evil_caster.messages[0]


def test_recharge_restores_charges(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Arcanist", level=50, is_npc=False)
    room = Room(vnum=5400)
    room.add_character(caster)
    caster.messages.clear()

    character_registry.append(caster)
    try:
        wand = ObjectData(
            item_type=int(ItemType.WAND),
            value=[0, 3, 1, 15, 0],
            short_descr="oak wand",
        )

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 30)
        success = skill_handlers.recharge(caster, wand)

        assert success is True
        assert wand.value[2] == 3
        assert wand.value[1] == 0
        assert "glows softly" in caster.messages[-1]

        caster.messages.clear()

        partial = ObjectData(
            item_type=int(ItemType.WAND),
            value=[0, 4, 1, 12, 0],
            short_descr="ash wand",
        )

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 80)
        partial_success = skill_handlers.recharge(caster, partial)

        assert partial_success is True
        assert partial.value[2] == 3
        assert partial.value[1] == 0
        assert caster.messages[-1] == "ash wand glows softly."
        assert caster.messages[-2] == "ash wand glows softly."
    finally:
        character_registry.remove(caster)


def test_recharge_failure_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Enchanter", level=30, is_npc=False)
    room = Room(vnum=5401)
    room.add_character(caster)
    caster.messages.clear()

    character_registry.append(caster)
    try:
        scroll = ObjectData(
            item_type=int(ItemType.SCROLL),
            value=[0, 0, 0, 0, 0],
            short_descr="tattered scroll",
        )

        assert skill_handlers.recharge(caster, scroll) is False
        assert caster.messages[-1] == "That item does not carry charges."

        caster.messages.clear()

        spent = ObjectData(
            item_type=int(ItemType.WAND),
            value=[0, 0, 0, 10, 0],
            short_descr="spent wand",
        )

        assert skill_handlers.recharge(caster, spent) is False
        assert caster.messages[-1] == "That item has already been recharged once."

        caster.messages.clear()

        fizz = ObjectData(
            item_type=int(ItemType.WAND),
            value=[0, 5, 3, 10, 0],
            short_descr="copper wand",
        )

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 92)
        fizzled = skill_handlers.recharge(caster, fizz)

        assert fizzled is False
        assert fizz.value[1] == 4
        assert fizz.value[2] == 3
        assert caster.messages[-1] == "Nothing seems to happen."

        caster.messages.clear()

        boom = ObjectData(
            item_type=int(ItemType.WAND),
            value=[0, 5, 2, 10, 0],
            short_descr="glass wand",
        )
        boom.carried_by = caster
        caster.inventory.append(boom)

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)
        exploded = skill_handlers.recharge(caster, boom)

        assert exploded is False
        assert boom not in caster.inventory
        assert "explodes" in caster.messages[-1]
    finally:
        character_registry.remove(caster)
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


def test_general_purpose_wand_damage_respects_override_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caster = Character(name="Collector", level=42, is_npc=False, hit=180, max_hit=180)
    victim = Character(name="Target Dummy", level=30, is_npc=True, hit=160, max_hit=160)
    room = Room(vnum=5100)
    room.add_character(caster)
    room.add_character(victim)

    caster.messages.clear()
    victim.messages.clear()

    wand_level = 14

    range_calls: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        range_calls.append((low, high))
        return 88

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    saves_calls: list[tuple[int, Character, DamageType]] = []

    def fake_saves(level: int, target: Character, damage_type: DamageType) -> bool:
        saves_calls.append((level, target, damage_type))
        return False

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.general_purpose(caster, victim, override_level=wand_level)

    assert damage == 88
    assert victim.hit == 72
    assert range_calls == [(25, 100)]
    assert saves_calls == [(wand_level, victim, DamageType.PIERCE)]
    assert any("general purpose ammo" in message for message in caster.messages)
    assert any("general purpose ammo" in message for message in victim.messages)


def test_high_explosive_wand_damage_respects_override_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caster = Character(name="Demolitionist", level=45, is_npc=False, hit=190, max_hit=190)
    victim = Character(name="Siege Dummy", level=32, is_npc=True, hit=170, max_hit=170)
    room = Room(vnum=5101)
    room.add_character(caster)
    room.add_character(victim)

    caster.messages.clear()
    victim.messages.clear()

    wand_level = 18

    range_calls: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        range_calls.append((low, high))
        return 117

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    saves_calls: list[tuple[int, Character, DamageType]] = []

    def fake_saves(level: int, target: Character, damage_type: DamageType) -> bool:
        saves_calls.append((level, target, damage_type))
        return True

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.high_explosive(caster, victim, override_level=wand_level)

    expected = c_div(117, 2)
    assert damage == expected
    assert victim.hit == 170 - expected
    assert range_calls == [(30, 120)]
    assert saves_calls == [(wand_level, victim, DamageType.PIERCE)]
    assert any("high explosive ammo" in message for message in caster.messages)
    assert any("high explosive ammo" in message for message in victim.messages)


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


def test_magic_missile_rolls_rom_damage_table(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Wizard", level=25, is_npc=False)
    victim = Character(name="Bandit", level=20, is_npc=False, hit=200, max_hit=200)
    room = Room(vnum=4102)
    room.add_character(caster)
    room.add_character(victim)

    ranges: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        ranges.append((low, high))
        return high

    save_calls: list[tuple[int, Character, DamageType]] = []

    def fake_saves(level: int, target: Character, damage_type: DamageType) -> bool:
        save_calls.append((level, target, damage_type))
        return False

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.magic_missile(caster, victim)

    assert ranges == [(c_div(9, 2), 18)]
    assert save_calls == [(25, victim, DamageType.ENERGY)]
    assert damage == 18
    assert victim.hit == 200 - 18


def test_magic_missile_save_halves_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Wizard", level=30, is_npc=False)
    victim = Character(name="Rogue", level=18, is_npc=False, hit=150, max_hit=150)
    room = Room(vnum=4103)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: 14)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: True)

    damage = skill_handlers.magic_missile(caster, victim)

    assert damage == c_div(14, 2)
    assert victim.hit == 150 - c_div(14, 2)


def test_lightning_bolt_rolls_rom_damage_table(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Stormcaller", level=35, is_npc=False)
    victim = Character(name="Marauder", level=28, is_npc=False, hit=260, max_hit=260)
    room = Room(vnum=4104)
    room.add_character(caster)
    room.add_character(victim)

    observed: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        observed.append((low, high))
        return high - 1

    save_args: list[tuple[int, Character, DamageType]] = []

    def fake_saves(level: int, target: Character, damage_type: DamageType) -> bool:
        save_args.append((level, target, damage_type))
        return False

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    damage = skill_handlers.lightning_bolt(caster, victim)

    assert observed == [(c_div(54, 2), 108)]
    assert save_args == [(35, victim, DamageType.LIGHTNING)]
    assert damage == 107
    assert victim.hit == 260 - 107


def test_lightning_bolt_save_halves_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Stormcaller", level=40, is_npc=False)
    victim = Character(name="Scout", level=22, is_npc=False, hit=220, max_hit=220)
    room = Room(vnum=4105)
    room.add_character(caster)
    room.add_character(victim)

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: 80)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: True)

    damage = skill_handlers.lightning_bolt(caster, victim)

    assert damage == c_div(80, 2)
    assert victim.hit == 220 - c_div(80, 2)


def test_energy_drain_siphons_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Warlock", level=32, is_npc=False, alignment=200, hit=120, max_hit=180)
    victim = Character(
        name="Adventurer",
        level=24,
        is_npc=False,
        hit=160,
        max_hit=160,
        mana=140,
        move=110,
        exp=4200,
    )
    room = Room(vnum=4300)
    room.add_character(caster)
    room.add_character(victim)

    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: 36)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 58)

    initial_exp = victim.exp
    initial_mana = victim.mana
    initial_move = victim.move
    initial_alignment = caster.alignment

    damage = skill_handlers.energy_drain(caster, victim)

    assert damage == 58
    assert victim.hit == 102
    assert caster.hit == 178
    assert victim.mana == c_div(initial_mana, 2)
    assert victim.move == c_div(initial_move, 2)

    min_exp = exp_per_level(victim)
    assert victim.exp == max(min_exp, initial_exp - 36)
    assert caster.alignment == max(-1000, initial_alignment - 50)

    assert any("life slipping away" in msg for msg in victim.messages)
    assert any("rush" in msg for msg in caster.messages)


def test_energy_drain_saves_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Necromancer", level=30, is_npc=False, alignment=150, hit=100, max_hit=150)
    victim = Character(name="Knight", level=28, is_npc=False, hit=180, max_hit=180, mana=160, move=130, exp=3900)
    room = Room(vnum=4301)
    room.add_character(caster)
    room.add_character(victim)

    caster.messages.clear()
    victim.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: True)

    initial_state = {
        "hit": victim.hit,
        "mana": victim.mana,
        "move": victim.move,
        "exp": victim.exp,
        "caster_hit": caster.hit,
        "caster_alignment": caster.alignment,
    }

    damage = skill_handlers.energy_drain(caster, victim)

    assert damage == 0
    assert victim.hit == initial_state["hit"]
    assert victim.mana == initial_state["mana"]
    assert victim.move == initial_state["move"]
    assert victim.exp == initial_state["exp"]
    assert caster.hit == initial_state["caster_hit"]
    assert caster.alignment == max(-1000, initial_state["caster_alignment"] - 50)

    assert victim.messages == ["You feel a momentary chill."]
    assert caster.messages == []


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

