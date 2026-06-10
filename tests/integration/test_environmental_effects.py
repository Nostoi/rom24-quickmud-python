"""Integration tests for environmental damage effects (effects.c).

Tests ROM C behavioral parity for acid, cold, fire, poison, and shock effects.
Verifies object destruction, container dumping, armor degradation, and affect application.

ROM C source: src/effects.c lines 39-615
"""

from __future__ import annotations

import pytest

import mud.magic.effects as _effects_mod
from mud.magic.effects import (
    SpellTarget,
    acid_effect,
    cold_effect,
    fire_effect,
    poison_effect,
    shock_effect,
)
from mud.models.character import Character
from mud.models.constants import ITEM_BLESS, ITEM_BURN_PROOF, ITEM_NOPURGE, AffectFlag, Condition, ItemType, Stat
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.utils import rng_mm


class _PCData:
    """Minimal pcdata stub: condition = [DRUNK, FULL, THIRST, HUNGER] (indices 0-3)."""

    def __init__(self, hunger: int = 48, thirst: int = 48) -> None:
        self.condition = [0, 48, thirst, hunger]  # [drunk=0, full=1, thirst=2, hunger=3]


def _make_pc_char(name: str, hunger: int = 48, thirst: int = 48) -> Character:
    pc = Character(name=name, is_npc=False, level=10, saving_throw=0, messages=[])
    pc.pcdata = _PCData(hunger=hunger, thirst=thirst)  # type: ignore[assignment]
    return pc


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

    def test_cold_fills_hunger(self, monkeypatch):
        """EFFECTS-001: cold_effect TARGET_CHAR must call gain_condition(victim, COND_HUNGER, dam/20).

        ROM C src/effects.c:235 — gain_condition (victim, COND_HUNGER, dam / 20);
        Positive delta fills hunger (URANGE(0, hunger+delta, 48)).
        Starting at hunger=10, dam=100 → gain=+5 → hunger should be 15.
        """
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        victim = _make_pc_char("Victim", hunger=10)
        cold_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)

        assert victim.pcdata.condition[int(Condition.HUNGER)] == 15  # 10 + (100//20)

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

    def test_fire_fills_thirst(self, monkeypatch):
        """EFFECTS-002: fire_effect TARGET_CHAR must call gain_condition(victim, COND_THIRST, dam/20).

        ROM C src/effects.c:341 — gain_condition (victim, COND_THIRST, dam / 20);
        Positive delta fills thirst (URANGE(0, thirst+delta, 48)).
        Starting at thirst=10, dam=100 → gain=+5 → thirst should be 15.
        """
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        victim = _make_pc_char("Victim", thirst=10)
        fire_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)

        assert victim.pcdata.condition[int(Condition.THIRST)] == 15  # 10 + (100//20)

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


# ---------------------------------------------------------------------------
# EFFECTS-003: cold_effect chill touch affect_join — ROM src/effects.c:224-230
# ---------------------------------------------------------------------------


class TestColdEffectChillTouch:
    """EFFECTS-003: cold_effect TARGET_CHAR applies chill touch SpellEffect on failed save.

    ROM C: src/effects.c:215-231 — affect_join with type=skill_lookup("chill touch"),
    level=level, duration=6, location=APPLY_STR, modifier=-1, bitvector=0.
    """

    def _make_char(self) -> Character:
        return Character(name="Vic", level=20, is_npc=False, saving_throw=0, messages=[])

    def test_chill_touch_affect_applied_on_failed_save(self, monkeypatch):
        # EFFECTS-003: failed save → SpellEffect "chill touch" (-1 STR, duration 6)
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        victim = self._make_char()
        cold_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        assert victim.has_spell_effect("chill touch"), "chill touch affect not applied"
        effect = victim.spell_effects["chill touch"]
        assert effect.duration == 6
        assert effect.stat_modifiers.get(Stat.STR) == -1

    def test_chill_touch_affect_not_applied_on_saved(self, monkeypatch):
        # EFFECTS-003: passed save → no chill touch affect
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: True)
        victim = self._make_char()
        cold_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        assert not victim.has_spell_effect("chill touch")

    def test_chill_touch_wear_off_message(self, monkeypatch):
        # ROM const.c:1042 — msg_off for "chill touch" is "You feel less cold."
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        victim = self._make_char()
        cold_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        effect = victim.spell_effects.get("chill touch")
        assert effect is not None
        assert effect.wear_off_message == "You feel less cold."


# ---------------------------------------------------------------------------
# EFFECTS-004: fire_effect fire breath blindness — ROM src/effects.c:328-336
# ---------------------------------------------------------------------------


class TestFireEffectBlindness:
    """EFFECTS-004: fire_effect TARGET_CHAR applies fire breath blindness on failed save.

    ROM C: src/effects.c:319-336 — affect_to_char with type=skill_lookup("fire breath"),
    level=level, duration=number_range(0, level/10), location=APPLY_HITROLL, modifier=-4,
    bitvector=AFF_BLIND.  Guarded by !IS_AFFECTED(victim, AFF_BLIND).
    """

    def _make_char(self, level: int = 20, blind: bool = False) -> Character:
        ch = Character(name="Vic", level=level, is_npc=False, saving_throw=0, messages=[])
        if blind:
            ch.affected_by |= int(AffectFlag.BLIND)
        return ch

    def test_fire_breath_blind_applied_on_failed_save(self, monkeypatch):
        # EFFECTS-004: failed save → AFF_BLIND set and SpellEffect "fire breath"
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        monkeypatch.setattr(_effects_mod.rng_mm, "number_range", lambda a, b: 2)
        victim = self._make_char(level=20)
        fire_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        assert victim.affected_by & int(AffectFlag.BLIND), "AFF_BLIND not set"
        assert victim.has_spell_effect("fire breath"), "fire breath affect not applied"
        effect = victim.spell_effects["fire breath"]
        assert effect.hitroll_mod == -4
        assert effect.duration == 2  # number_range forced to 2

    def test_fire_breath_duration_bounded(self, monkeypatch):
        # duration = number_range(0, level/10) — ensure bounds respected
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        monkeypatch.setattr(_effects_mod.rng_mm, "number_range", lambda a, b: b)
        victim = self._make_char(level=30)
        fire_effect(victim, level=30, damage=100, target_type=SpellTarget.TARGET_CHAR)
        effect = victim.spell_effects.get("fire breath")
        assert effect is not None
        assert effect.duration <= 30 // 10  # level/10 = 3

    def test_fire_breath_skipped_when_already_blind(self, monkeypatch):
        # ROM L320: !IS_AFFECTED(victim, AFF_BLIND) guard — already blind → skip
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        victim = self._make_char(blind=True)
        fire_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        assert not victim.has_spell_effect("fire breath"), "should not re-apply when already blind"

    def test_fire_breath_not_applied_on_saved(self, monkeypatch):
        # EFFECTS-004: passed save → no blindness
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: True)
        victim = self._make_char()
        fire_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        assert not (victim.affected_by & int(AffectFlag.BLIND))

    def test_fire_breath_wear_off_message(self, monkeypatch):
        # ROM const.c:1515 — msg_off for "fire breath" is "The smoke leaves your eyes."
        monkeypatch.setattr(_effects_mod, "saves_spell", lambda *_: False)
        monkeypatch.setattr(_effects_mod.rng_mm, "number_range", lambda a, b: 1)
        victim = self._make_char()
        fire_effect(victim, level=20, damage=100, target_type=SpellTarget.TARGET_CHAR)
        effect = victim.spell_effects.get("fire breath")
        assert effect is not None
        assert effect.wear_off_message == "The smoke leaves your eyes."
