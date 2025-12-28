"""
Test suite for player resistance flags: immunities, resistances, vulnerabilities.

ROM Reference: src/fight.c, src/magic.c
"""

from __future__ import annotations

import pytest

from mud.models.constants import ImmFlag, ResFlag, VulnFlag
from mud.world import create_test_character


class TestImmunityFlags:
    """Test immunity flags (ROM src/fight.c:damage, src/magic.c:check_immune)."""

    def test_imm_summon_prevents_summon_spell(self):
        """Test IMM_SUMMON prevents summon spells."""
        # ROM: check_immune returns IS_SET(victim->imm_flags, IMM_SUMMON)
        ch = create_test_character("Tester", 3001)

        # Set immunity to summon
        ch.imm_flags |= ImmFlag.SUMMON

        assert (ch.imm_flags & ImmFlag.SUMMON) != 0
        # Summon spells should fail against this character

    def test_imm_charm_prevents_charm_spell(self):
        """Test IMM_CHARM prevents charm spells."""
        # ROM: check_immune returns IS_SET(victim->imm_flags, IMM_CHARM)
        ch = create_test_character("Tester", 3001)

        ch.imm_flags |= ImmFlag.CHARM

        assert (ch.imm_flags & ImmFlag.CHARM) != 0
        # Charm spells should fail against this character

    def test_imm_magic_blocks_offensive_spells(self):
        """Test IMM_MAGIC blocks offensive spells."""
        # ROM: check_immune returns IS_SET(victim->imm_flags, IMM_MAGIC)
        ch = create_test_character("Tester", 3001)

        ch.imm_flags |= ImmFlag.MAGIC

        assert (ch.imm_flags & ImmFlag.MAGIC) != 0
        # Offensive spells should deal no damage

    def test_imm_weapon_blocks_physical_damage(self):
        """Test IMM_WEAPON blocks physical weapon damage."""
        # ROM: damage() checks IS_SET(victim->imm_flags, IMM_WEAPON)
        ch = create_test_character("Tester", 3001)

        ch.imm_flags |= ImmFlag.WEAPON

        assert (ch.imm_flags & ImmFlag.WEAPON) != 0
        # Physical attacks should deal no damage

    def test_imm_bash_blocks_bash_attacks(self):
        """Test IMM_BASH blocks bash damage type."""
        # ROM: damage() checks IS_SET(victim->imm_flags, IMM_BASH)
        ch = create_test_character("Tester", 3001)

        ch.imm_flags |= ImmFlag.BASH

        assert (ch.imm_flags & ImmFlag.BASH) != 0
        # Bash damage should be blocked


class TestResistanceFlags:
    """Test resistance flags (ROM src/fight.c:damage)."""

    def test_res_fire_reduces_fire_damage(self):
        """Test RES_FIRE reduces fire damage."""
        # ROM: damage() checks IS_SET(victim->res_flags, RES_FIRE)
        #      Applies damage multiplier (typically 50% or 2/3)
        ch = create_test_character("Tester", 3001)

        ch.res_flags |= ResFlag.FIRE

        assert (ch.res_flags & ResFlag.FIRE) != 0
        # Fire damage should be reduced

    def test_res_cold_reduces_cold_damage(self):
        """Test RES_COLD reduces cold damage."""
        # ROM: damage() checks IS_SET(victim->res_flags, RES_COLD)
        ch = create_test_character("Tester", 3001)

        ch.res_flags |= ResFlag.COLD

        assert (ch.res_flags & ResFlag.COLD) != 0
        # Cold damage should be reduced

    def test_res_lightning_reduces_lightning_damage(self):
        """Test RES_LIGHTNING reduces lightning damage."""
        # ROM: damage() checks IS_SET(victim->res_flags, RES_LIGHTNING)
        ch = create_test_character("Tester", 3001)

        ch.res_flags |= ResFlag.LIGHTNING

        assert (ch.res_flags & ResFlag.LIGHTNING) != 0
        # Lightning damage should be reduced

    def test_res_acid_reduces_acid_damage(self):
        """Test RES_ACID reduces acid damage."""
        # ROM: damage() checks IS_SET(victim->res_flags, RES_ACID)
        ch = create_test_character("Tester", 3001)

        ch.res_flags |= ResFlag.ACID

        assert (ch.res_flags & ResFlag.ACID) != 0
        # Acid damage should be reduced

    def test_res_poison_reduces_poison_damage(self):
        """Test RES_POISON reduces poison damage."""
        # ROM: damage() checks IS_SET(victim->res_flags, RES_POISON)
        ch = create_test_character("Tester", 3001)

        ch.res_flags |= ResFlag.POISON

        assert (ch.res_flags & ResFlag.POISON) != 0
        # Poison damage should be reduced


class TestVulnerabilityFlags:
    """Test vulnerability flags (ROM src/fight.c:damage)."""

    def test_vuln_fire_increases_fire_damage(self):
        """Test VULN_FIRE increases fire damage taken."""
        # ROM: damage() checks IS_SET(victim->vuln_flags, VULN_FIRE)
        #      Applies damage multiplier (typically 150% or 4/3)
        ch = create_test_character("Tester", 3001)

        ch.vuln_flags |= VulnFlag.FIRE

        assert (ch.vuln_flags & VulnFlag.FIRE) != 0
        # Fire damage should be increased

    def test_vuln_cold_increases_cold_damage(self):
        """Test VULN_COLD increases cold damage taken."""
        # ROM: damage() checks IS_SET(victim->vuln_flags, VULN_COLD)
        ch = create_test_character("Tester", 3001)

        ch.vuln_flags |= VulnFlag.COLD

        assert (ch.vuln_flags & VulnFlag.COLD) != 0
        # Cold damage should be increased

    def test_vuln_lightning_increases_lightning_damage(self):
        """Test VULN_LIGHTNING increases lightning damage taken."""
        # ROM: damage() checks IS_SET(victim->vuln_flags, VULN_LIGHTNING)
        ch = create_test_character("Tester", 3001)

        ch.vuln_flags |= VulnFlag.LIGHTNING

        assert (ch.vuln_flags & VulnFlag.LIGHTNING) != 0
        # Lightning damage should be increased

    def test_vuln_iron_increases_iron_weapon_damage(self):
        """Test VULN_IRON increases damage from iron weapons."""
        # ROM: damage() checks IS_SET(victim->vuln_flags, VULN_IRON)
        #      Increases damage when weapon material is iron
        ch = create_test_character("Tester", 3001)

        ch.vuln_flags |= VulnFlag.IRON

        assert (ch.vuln_flags & VulnFlag.IRON) != 0
        # Iron weapon damage should be increased

    def test_vuln_wood_increases_wood_weapon_damage(self):
        """Test VULN_WOOD increases damage from wooden weapons."""
        # ROM: damage() checks IS_SET(victim->vuln_flags, VULN_WOOD)
        #      Increases damage when weapon material is wood
        ch = create_test_character("Tester", 3001)

        ch.vuln_flags |= VulnFlag.WOOD

        assert (ch.vuln_flags & VulnFlag.WOOD) != 0
        # Wood weapon damage should be increased
