"""Integration tests for environmental damage effects (effects.c).

Tests ROM C behavioral parity for acid, cold, fire, poison, and shock effects.
Verifies object destruction, container dumping, armor degradation, and affect application.

ROM C source: src/effects.c lines 39-615
"""

from __future__ import annotations

import pytest

from mud.magic.effects import (
    SpellTarget,
    acid_effect,
    cold_effect,
    fire_effect,
    poison_effect,
    shock_effect,
)
from mud.models.character import Character
from mud.models.constants import ITEM_BLESS, ITEM_BURN_PROOF, ITEM_NOPURGE, ItemType
from mud.models.object import Object
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.utils import rng_mm


@pytest.fixture
def test_room():
    return Room(vnum=1, name="Test Room", description="A test room", sector_type=0)


@pytest.fixture
def test_char():
    return Character(
        name="TestChar",
        level=40,
        hit=100,
        max_hit=100,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        is_npc=False,
        saving_throw=0,
        messages=[],
        inventory=[],
    )


def create_test_object(item_type: ItemType, level: int = 10, extra_flags: int = 0) -> Object:
    proto = ObjIndex(
        vnum=9999,
        short_descr="test item",
        description="test item desc",
        item_type=int(item_type),
        level=level,
        extra_flags=extra_flags,
        value=[0, 0, 0, 0, 0],
    )
    return Object(instance_id=9999, prototype=proto, extra_flags=extra_flags, level=level)


class TestPoisonEffect:
    def test_poison_food_item(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        food = create_test_object(ItemType.FOOD, level=10)
        assert food.value[3] == 0

        poison_effect(food, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert food.value[3] == 1

    def test_poison_drink_container(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        drink = create_test_object(ItemType.DRINK_CON, level=10)
        drink.value = [50, 100, 0, 0, 0]

        poison_effect(drink, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert drink.value[3] == 1

    def test_poison_empty_drink_immune(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        empty_drink = create_test_object(ItemType.DRINK_CON, level=10)
        empty_drink.value = [100, 100, 0, 0, 0]

        poison_effect(empty_drink, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert empty_drink.value[3] == 0

    def test_poison_blessed_item_immune(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        blessed_food = create_test_object(ItemType.FOOD, level=10, extra_flags=ITEM_BLESS)

        poison_effect(blessed_food, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert blessed_food.value[3] == 0

    def test_poison_burn_proof_immune(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        burn_proof_food = create_test_object(ItemType.FOOD, level=10, extra_flags=ITEM_BURN_PROOF)

        poison_effect(burn_proof_food, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert burn_proof_food.value[3] == 0


class TestColdEffect:
    def test_cold_shatters_potion(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        potion = create_test_object(ItemType.POTION, level=1)
        original_id = id(potion)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        cold_effect(potion, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_cold_shatters_drink_container(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        drink = create_test_object(ItemType.DRINK_CON, level=1)
        original_id = id(drink)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        cold_effect(drink, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_cold_burn_proof_immune(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        burn_proof_potion = create_test_object(ItemType.POTION, level=1, extra_flags=ITEM_BURN_PROOF)
        original_id = id(burn_proof_potion)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        cold_effect(burn_proof_potion, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id not in extracted_objects


class TestFireEffect:
    def test_fire_burns_scroll(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        scroll = create_test_object(ItemType.SCROLL, level=1)
        original_id = id(scroll)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        fire_effect(scroll, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_fire_burns_food(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        food = create_test_object(ItemType.FOOD, level=1)
        original_id = id(food)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        fire_effect(food, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_fire_burn_proof_immune(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        burn_proof_scroll = create_test_object(ItemType.SCROLL, level=1, extra_flags=ITEM_BURN_PROOF)
        original_id = id(burn_proof_scroll)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        fire_effect(burn_proof_scroll, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id not in extracted_objects


class TestShockEffect:
    def test_shock_destroys_wand(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        wand = create_test_object(ItemType.WAND, level=1)
        original_id = id(wand)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        shock_effect(wand, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_shock_destroys_staff(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        staff = create_test_object(ItemType.STAFF, level=1)
        original_id = id(staff)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        shock_effect(staff, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_shock_destroys_jewelry(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        jewelry = create_test_object(ItemType.JEWELRY, level=1)
        original_id = id(jewelry)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        shock_effect(jewelry, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_shock_daze_character(self, test_char, monkeypatch):
        # Patch saves_spell in the effects module where it's imported
        monkeypatch.setattr("mud.magic.effects.saves_spell", lambda *args, **kwargs: False)

        assert getattr(test_char, "daze", 0) == 0

        shock_effect(test_char, level=40, damage=100, target_type=SpellTarget.TARGET_CHAR)

        assert test_char.daze > 0


class TestAcidEffect:
    def test_acid_degrades_armor_ac(self, monkeypatch):
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        armor = create_test_object(ItemType.ARMOR, level=1)
        original_id = id(armor)

        extracted_objects = []

        def mock_extract(obj):
            extracted_objects.append(id(obj))

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        acid_effect(armor, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id not in extracted_objects

        assert len(armor.affected) > 0
        ac_affect = next((a for a in armor.affected if a.location == 1), None)
        assert ac_affect is not None
        assert ac_affect.modifier == 1

    def test_acid_destroys_clothing(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        clothing = create_test_object(ItemType.CLOTHING, level=1)
        original_id = id(clothing)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        acid_effect(clothing, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id in extracted_objects

    def test_acid_nopurge_immune(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        nopurge_clothing = create_test_object(ItemType.CLOTHING, level=1, extra_flags=ITEM_NOPURGE)
        original_id = id(nopurge_clothing)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        acid_effect(nopurge_clothing, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id not in extracted_objects

    def test_acid_blessed_item_reduces_chance(self, monkeypatch):
        from mud.game_loop import _extract_obj

        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 100)

        blessed_clothing = create_test_object(ItemType.CLOTHING, level=1, extra_flags=ITEM_BLESS)
        original_id = id(blessed_clothing)

        extracted_objects = []
        original_extract = _extract_obj

        def mock_extract(obj):
            extracted_objects.append(id(obj))
            return original_extract(obj)

        monkeypatch.setattr("mud.magic.effects._get_extract_obj", lambda: mock_extract)

        acid_effect(blessed_clothing, level=40, damage=100, target_type=SpellTarget.TARGET_OBJ)

        assert original_id not in extracted_objects


class TestProbabilityFormula:
    def test_higher_level_increases_chance(self, monkeypatch):
        from mud.magic.effects import _calculate_chance

        obj = create_test_object(ItemType.SCROLL, level=1)

        low_chance = _calculate_chance(level=10, damage=20, obj=obj)
        high_chance = _calculate_chance(level=40, damage=20, obj=obj)

        assert high_chance > low_chance

    def test_higher_damage_increases_chance(self, monkeypatch):
        from mud.magic.effects import _calculate_chance

        obj = create_test_object(ItemType.SCROLL, level=1)

        low_chance = _calculate_chance(level=20, damage=10, obj=obj)
        high_chance = _calculate_chance(level=20, damage=100, obj=obj)

        assert high_chance > low_chance

    def test_blessed_reduces_chance(self, monkeypatch):
        from mud.magic.effects import _calculate_chance

        normal_obj = create_test_object(ItemType.SCROLL, level=1)
        blessed_obj = create_test_object(ItemType.SCROLL, level=1, extra_flags=ITEM_BLESS)

        normal_chance = _calculate_chance(level=20, damage=50, obj=normal_obj)
        blessed_chance = _calculate_chance(level=20, damage=50, obj=blessed_obj)

        assert blessed_chance < normal_chance
        # BLESS reduces by 5, but clamping to min 5 means actual diff may be less
        # normal: 20/4 + 50/10 - 1*2 = 5 + 5 - 2 = 8
        # blessed: 20/4 + 50/10 - 5 - 1*2 = 5 + 5 - 5 - 2 = 3, clamped to 5
        assert blessed_chance == 5  # Clamped to minimum
        assert normal_chance == 8

    def test_clamped_to_5_95_range(self, monkeypatch):
        from mud.magic.effects import _calculate_chance

        low_obj = create_test_object(ItemType.SCROLL, level=50)

        low_chance = _calculate_chance(level=1, damage=1, obj=low_obj)
        assert low_chance >= 5

        high_obj = create_test_object(ItemType.SCROLL, level=1)
        high_chance = _calculate_chance(level=100, damage=1000, obj=high_obj)
        assert high_chance <= 95
