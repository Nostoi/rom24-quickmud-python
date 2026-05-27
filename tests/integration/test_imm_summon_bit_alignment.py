"""Regression for PARALLEL-002: NPC nosummon toggle read the wrong IMM_SUMMON bit.

`mud/commands/player_config.py:do_nosummon` for NPCs declared inline
`IMM_SUMMON = 0x00000010` (bit 4) instead of the canonical
`DefenseBit.SUMMON` (ROM `A = 1<<0 = 0x1`). The function is the gate
for the NPC `nosummon` toggle, so pre-fix:

- NPCs flagged with canonical `DefenseBit.SUMMON` could be summoned freely.
- NPCs flagged with bit 4 (unrelated) were spuriously immune to summoning.

ROM C: `src/merc.h` defines the COMM_* and IMM_* macros using letter slots,
where SUMMON/CHARM/MAGIC etc. are the A-Z positions (0-25 bits). The canonical
IntEnum `DefenseBit.SUMMON` maps to `1<<0`.
"""

from __future__ import annotations

import pytest

from mud.commands.player_config import do_nosummon
from mud.models.character import Character
from mud.models.constants import DefenseBit


@pytest.fixture
def npc() -> Character:
    char = Character(name="NoSummonTester", level=10, is_npc=True)
    char.imm_flags = 0
    return char


def test_npc_with_canonical_summon_bit_can_toggle_nosummon(npc: Character) -> None:
    """NPC with canonical DefenseBit.SUMMON set should recognize it and toggle off."""
    # Set the canonical SUMMON bit on the NPC (bit 0 = 0x1)
    npc.imm_flags = int(DefenseBit.SUMMON)

    # Calling do_nosummon should toggle it off
    result = do_nosummon(npc, "")
    assert "no longer immune" in result.lower()
    assert npc.imm_flags == 0


def test_npc_without_summon_bit_can_set_nosummon(npc: Character) -> None:
    """NPC without SUMMON bit set should be able to set it via nosummon."""
    # Start with no SUMMON bit
    npc.imm_flags = 0

    # Calling do_nosummon should set it to the canonical bit
    result = do_nosummon(npc, "")
    assert "now immune to summoning" in result.lower()
    assert npc.imm_flags == int(DefenseBit.SUMMON)


def test_npc_toggle_uses_canonical_bit_not_hardcoded_0x10(npc: Character) -> None:
    """Verify the toggle uses DefenseBit.SUMMON (0x1) not hardcoded 0x10."""
    # Set bit 4 (0x10) which should NOT be the SUMMON bit
    npc.imm_flags = 0x10

    # Calling do_nosummon should NOT toggle bit 4;
    # it should set bit 0 (canonical SUMMON)
    result = do_nosummon(npc, "")
    assert "now immune to summoning" in result.lower()
    assert npc.imm_flags == 0x10 | int(DefenseBit.SUMMON)
    assert npc.imm_flags == 0x11  # bit 4 + bit 0
