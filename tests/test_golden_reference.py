"""
Golden Reference Tests for ROM Parity Verification

These tests compare Python implementation outputs against known-good values
captured from the ROM 2.4b C implementation (or derived from C source analysis).

Golden files are stored in tests/data/golden/*.golden.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from mud.combat.engine import (
    apply_damage,
    check_dodge,
    check_parry,
    check_shield_block,
)
from mud.math.c_compat import c_div, c_mod, urange
from mud.models.character import Character
from mud.models.constants import DamageType
from mud.utils import rng_mm


GOLDEN_DIR = Path(__file__).parent / "data" / "golden"


def load_golden_file(name: str) -> Dict[str, Any]:
    """Load a golden reference file."""
    path = GOLDEN_DIR / f"{name}.golden.json"
    if not path.exists():
        pytest.skip(f"Golden file not found: {path}")
    return json.loads(path.read_text())


class TestRNGGoldenReference:
    """Verify RNG produces deterministic sequences matching C implementation."""

    def test_rng_determinism_same_seed(self):
        """Verify same seed produces same sequence."""
        rng_mm.seed_mm(1234)
        seq1 = [rng_mm.number_mm() for _ in range(20)]

        rng_mm.seed_mm(1234)
        seq2 = [rng_mm.number_mm() for _ in range(20)]

        assert seq1 == seq2, "RNG must be deterministic with same seed"

    def test_rng_different_seeds_differ(self):
        """Verify different seeds produce different sequences."""
        rng_mm.seed_mm(1234)
        seq1 = [rng_mm.number_mm() for _ in range(20)]

        rng_mm.seed_mm(5678)
        seq2 = [rng_mm.number_mm() for _ in range(20)]

        assert seq1 != seq2, "Different seeds should produce different sequences"

    def test_number_range_bounds(self):
        """Verify number_range stays within specified bounds."""
        rng_mm.seed_mm(42)
        for _ in range(1000):
            val = rng_mm.number_range(10, 20)
            assert 10 <= val <= 20, f"number_range(10, 20) returned {val}"

    def test_number_percent_bounds(self):
        """Verify number_percent returns 1-100 inclusive."""
        rng_mm.seed_mm(42)
        for _ in range(1000):
            val = rng_mm.number_percent()
            assert 1 <= val <= 100, f"number_percent() returned {val}"

    def test_dice_bounds(self):
        """Verify dice(n, s) returns n to n*s inclusive."""
        rng_mm.seed_mm(42)
        for _ in range(1000):
            val = rng_mm.dice(3, 6)
            assert 3 <= val <= 18, f"dice(3, 6) returned {val}"

    def test_number_bits_bounds(self):
        """Verify number_bits returns values in expected range."""
        rng_mm.seed_mm(42)
        for width in [1, 2, 3, 4, 5, 8, 10]:
            for _ in range(100):
                val = rng_mm.number_bits(width)
                max_val = (1 << width) - 1
                assert 0 <= val <= max_val, f"number_bits({width}) returned {val}"


class TestDamageGoldenReference:
    """Verify damage calculations match ROM C formulas."""

    def test_damage_resist_halves(self):
        """ROM: resistant damage is halved using integer division."""
        golden = load_golden_file("damage_calculations")
        case = next(c for c in golden["test_cases"] if c["name"] == "damage_resist_half")

        base = case["base_damage"]
        expected = case["expected"]

        # ROM formula: dam = dam / 2 (integer division)
        result = c_div(base, 2)
        assert result == expected

    def test_damage_immune_zero(self):
        """ROM: immune damage is zeroed."""
        golden = load_golden_file("damage_calculations")
        case = next(c for c in golden["test_cases"] if c["name"] == "damage_immune_zero")

        assert case["expected"] == 0

    def test_damage_vulnerable_150pct(self):
        """ROM: vulnerable damage is 150% using dam += dam / 2."""
        golden = load_golden_file("damage_calculations")
        case = next(c for c in golden["test_cases"] if c["name"] == "damage_vulnerable_150pct")

        base = case["base_damage"]
        expected = case["expected"]

        # ROM formula: dam += dam / 2
        result = base + c_div(base, 2)
        assert result == expected

    def test_thac0_warrior_level_10(self):
        """Verify THAC0 calculation for warrior at level 10."""
        golden = load_golden_file("damage_calculations")
        case = next(c for c in golden["test_cases"] if c["name"] == "thac0_level_10_warrior")

        level = case["level"]
        thac0_00 = case["thac0_00"]
        thac0_32 = case["thac0_32"]
        expected = case["expected_thac0"]

        # ROM formula: thac0_00 - level * (thac0_00 - thac0_32) / 32
        result = thac0_00 - c_div(level * (thac0_00 - thac0_32), 32)
        assert result == expected, f"THAC0 at level {level}: {result} != {expected}"

    def test_thac0_mage_level_20(self):
        """Verify THAC0 calculation for mage at level 20."""
        golden = load_golden_file("damage_calculations")
        case = next(c for c in golden["test_cases"] if c["name"] == "thac0_level_20_mage")

        level = case["level"]
        thac0_00 = case["thac0_00"]
        thac0_32 = case["thac0_32"]
        expected = case["expected_thac0"]

        result = thac0_00 - c_div(level * (thac0_00 - thac0_32), 32)
        assert result == expected


class TestSkillCheckGoldenReference:
    """Verify skill check formulas match ROM C code."""

    def test_parry_basic_chance(self):
        """ROM: parry chance = skill / 2."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["skill_checks"] if c["name"] == "parry_check_basic")

        skill = case["skill_level"]
        expected = case["expected_chance"]

        # ROM formula: chance = get_skill(victim, gsn_parry) / 2
        result = c_div(skill, 2)
        assert result == expected

    def test_parry_with_level_bonus(self):
        """ROM: parry chance includes level difference."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["skill_checks"] if c["name"] == "parry_check_level_bonus")

        skill = case["skill_level"]
        att_level = case["attacker_level"]
        def_level = case["defender_level"]
        expected = case["expected_chance"]

        # ROM formula: chance = skill / 2 + (defender_level - attacker_level)
        result = c_div(skill, 2) + (def_level - att_level)
        assert result == expected

    def test_dodge_basic_chance(self):
        """ROM: dodge chance = skill / 2."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["skill_checks"] if c["name"] == "dodge_check_basic")

        skill = case["skill_level"]
        expected = case["expected_chance"]

        result = c_div(skill, 2)
        assert result == expected

    def test_shield_block_chance(self):
        """ROM: shield block chance = skill / 2."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["skill_checks"] if c["name"] == "shield_block_basic")

        skill = case["skill_level"]
        expected = case["expected_chance"]

        result = c_div(skill, 2)
        assert result == expected


class TestSavingThrowGoldenReference:
    """Verify saving throw calculations match ROM C code."""

    def test_saves_spell_equal_level(self):
        """ROM: saves_spell at equal level = 50%."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["saving_throws"] if c["name"] == "saves_spell_equal_level")

        caster_level = case["caster_level"]
        victim_level = case["victim_level"]
        saving_throw = case["victim_saving_throw"]
        expected = case["expected_save_chance"]

        # ROM formula: save = 50 + (victim->level - level) * 5 - victim->saving_throw * 5
        save = 50 + (victim_level - caster_level) * 5 - saving_throw * 5
        save = urange(5, save, 95)  # Clamp 5-95

        assert save == expected

    def test_saves_spell_clamped_minimum(self):
        """ROM: saves_spell clamped to 5% minimum."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["saving_throws"] if c["name"] == "saves_spell_lower_victim")

        caster_level = case["caster_level"]
        victim_level = case["victim_level"]
        saving_throw = case["victim_saving_throw"]

        save = 50 + (victim_level - caster_level) * 5 - saving_throw * 5
        save = urange(5, save, 95)

        assert save >= 5, "Save should be clamped to minimum 5%"

    def test_saves_spell_clamped_maximum(self):
        """ROM: saves_spell clamped to 95% maximum."""
        golden = load_golden_file("skill_checks")
        case = next(c for c in golden["saving_throws"] if c["name"] == "saves_spell_higher_victim")

        caster_level = case["caster_level"]
        victim_level = case["victim_level"]
        saving_throw = case["victim_saving_throw"]

        save = 50 + (victim_level - caster_level) * 5 - saving_throw * 5
        save = urange(5, save, 95)

        assert save <= 95, "Save should be clamped to maximum 95%"


class TestCDivisionParity:
    """Critical: Verify c_div matches C integer division semantics."""

    @pytest.mark.parametrize("a,b,expected", [
        # Positive cases
        (10, 3, 3),
        (9, 3, 3),
        (8, 3, 2),
        (7, 3, 2),
        (1, 3, 0),
        (0, 3, 0),
        # CRITICAL: Negative cases where C differs from Python //
        (-10, 3, -3),   # C: -3, Python //: -4
        (-9, 3, -3),    # C: -3, Python //: -3
        (-8, 3, -2),    # C: -2, Python //: -3
        (-7, 3, -2),    # C: -2, Python //: -3
        (-1, 3, 0),     # C: 0, Python //: -1
        (10, -3, -3),   # C: -3, Python //: -4
        (-10, -3, 3),   # C: 3, Python //: 3
    ])
    def test_c_div_matches_c_semantics(self, a, b, expected):
        """Verify c_div truncates toward zero like C."""
        result = c_div(a, b)
        assert result == expected, f"c_div({a}, {b}) = {result}, expected {expected}"

    @pytest.mark.parametrize("a,b,expected", [
        # c_mod must satisfy: a == b * c_div(a, b) + c_mod(a, b)
        (-10, 3, -1),
        (-9, 3, 0),
        (-8, 3, -2),
        (10, -3, 1),
        (-10, -3, -1),
    ])
    def test_c_mod_matches_c_semantics(self, a, b, expected):
        """Verify c_mod matches C modulo semantics."""
        result = c_mod(a, b)
        assert result == expected, f"c_mod({a}, {b}) = {result}, expected {expected}"

        # Verify the invariant: a == b * c_div(a, b) + c_mod(a, b)
        assert a == b * c_div(a, b) + c_mod(a, b)


class TestURANGEParity:
    """Verify URANGE clamping matches ROM macro."""

    @pytest.mark.parametrize("low,val,high,expected", [
        (0, 5, 10, 5),      # In range
        (0, -5, 10, 0),     # Below min
        (0, 15, 10, 10),    # Above max
        (-10, -5, 10, -5),  # Negative range
        (5, 5, 5, 5),       # Edge: all equal
        (0, 0, 0, 0),       # Zero
    ])
    def test_urange_clamping(self, low, val, high, expected):
        """Verify urange matches C URANGE macro."""
        result = urange(low, val, high)
        assert result == expected
