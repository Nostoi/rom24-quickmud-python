"""
Integration tests for do_affects command (ROM C parity verification).

ROM Reference: src/act_info.c do_affects (lines 1714-1755)

Tests verify:
- No affects message
- Level <20 simple format (spell name only)
- Level 20+ detailed format (modifier, location, duration)
- Permanent duration display
- Stacked affects (same spell, multiple modifiers)
- Affect deduplication for level <20
"""

from __future__ import annotations

import pytest

from mud.commands.affects import do_affects
from mud.models.character import Character, SpellEffect, AffectData
from mud.models.constants import Stat


# ROM C APPLY_* constants (from src/merc.h lines 1205-1231)
APPLY_STR = 1
APPLY_AC = 17
APPLY_HITROLL = 18
APPLY_DAMROLL = 19
APPLY_SAVING_SPELL = 24


def test_affects_no_affects():
    """Test affects when character has no affects."""
    char = Character(name="TestChar", level=1)
    result = do_affects(char, "")
    assert "You are not affected by any spells" in result


def test_affects_simple_format_level_under_20():
    """Test affects shows simple format for level <20."""
    char = Character(name="TestChar", level=10)

    # Add bless spell via SpellEffect (auto-syncs to ch.affected)
    effect = SpellEffect(name="bless", duration=10, level=10, saving_throw_mod=-1)
    char.apply_spell_effect(effect)

    result = do_affects(char, "")
    assert "Spell: bless" in result
    assert "modifies" not in result  # Level <20 hides details


def test_affects_detailed_format_level_20_plus():
    """Test affects shows detailed format for level 20+."""
    char = Character(name="TestChar", level=20)

    effect = SpellEffect(name="bless", duration=10, level=20, saving_throw_mod=-1)
    char.apply_spell_effect(effect)

    result = do_affects(char, "")
    assert "Spell: bless" in result
    assert "modifies saves by -1 for 10 hours" in result


def test_affects_permanent_duration():
    """Test affects shows 'permanently' for duration=-1."""
    char = Character(name="TestChar", level=20)

    # Add shield spell with permanent duration
    effect = SpellEffect(name="shield", duration=-1, level=20, ac_mod=-20)
    char.apply_spell_effect(effect)

    result = do_affects(char, "")
    assert "permanently" in result
    assert "shield" in result


def test_affects_stacked_same_spell():
    """Test affects shows multiple modifiers from same spell."""
    char = Character(name="TestChar", level=20)

    # Add giant_strength spell (modifies STR and HITROLL)
    effect = SpellEffect(name="giant strength", duration=5, level=20, hitroll_mod=1, stat_modifiers={Stat.STR: 1})
    char.apply_spell_effect(effect)

    result = do_affects(char, "")
    lines = result.split("\n")

    # Should have 3 lines total:
    # 1. "You are affected by the following spells:"
    # 2. "Spell: giant strength: modifies hitroll by +1 for 5 hours"
    # 3. "                      : modifies strength by +1 for 5 hours" (indented)

    assert len(lines) == 3
    assert "giant strength" in lines[1]
    assert "modifies" in lines[1]
    assert "modifies" in lines[2]

    # Verify one line has hitroll, another has strength
    result_lower = result.lower()
    assert "hit roll" in result_lower
    assert "strength" in result_lower


def test_affects_deduplication_level_under_20():
    """Test affects hides duplicate spells for level <20."""
    char = Character(name="TestChar", level=10)

    # Manually add two affects with same spell name (different locations)
    # This simulates a spell with multiple modifiers
    affect1 = AffectData(
        type="bless",  # type: ignore - using string temporarily
        level=10,
        duration=10,
        location=APPLY_SAVING_SPELL,
        modifier=-1,
        bitvector=0,
    )
    affect2 = AffectData(
        type="bless",  # type: ignore
        level=10,
        duration=10,
        location=APPLY_HITROLL,
        modifier=1,
        bitvector=0,
    )
    char.affected.append(affect1)
    char.affected.append(affect2)

    result = do_affects(char, "")

    # Level <20 should only show "Spell: bless" once (skips duplicates)
    assert result.count("bless") == 1
    assert "modifies" not in result  # No detailed info at level <20


def test_affects_modifier_formatting():
    """Test modifier formatting with positive, negative, and zero values.

    ROM C uses raw %d format (no explicit + sign).
    ROM Reference: src/act_info.c line 1737
    """
    char = Character(name="TestChar", level=20)

    # Test positive modifier
    effect1 = SpellEffect(name="haste", duration=5, level=20, hitroll_mod=2)
    char.apply_spell_effect(effect1)

    # Test negative modifier
    effect2 = SpellEffect(name="curse", duration=10, level=20, saving_throw_mod=-3)
    char.apply_spell_effect(effect2)

    result = do_affects(char, "")

    # ROM C shows raw number (no + sign for positive)
    assert "by 2 for" in result  # Positive modifier shown as raw "2"

    # Negative modifier keeps "-" sign
    assert "by -3 for" in result


def test_affects_multiple_different_spells():
    """Test affects displays multiple different spells correctly."""
    char = Character(name="TestChar", level=20)

    # Add multiple different spells
    effect1 = SpellEffect(name="armor", duration=24, level=20, ac_mod=-20)
    effect2 = SpellEffect(name="bless", duration=10, level=20, saving_throw_mod=-1)
    effect3 = SpellEffect(name="haste", duration=5, level=20, hitroll_mod=1)

    char.apply_spell_effect(effect1)
    char.apply_spell_effect(effect2)
    char.apply_spell_effect(effect3)

    result = do_affects(char, "")
    lines = result.split("\n")

    # Should have 4 lines (header + 3 spells)
    assert len(lines) == 4
    assert "armor" in result
    assert "bless" in result
    assert "haste" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
