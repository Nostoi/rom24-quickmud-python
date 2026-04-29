"""ROM ``src/tables.c`` parity reproducers.

These tests pin down ROM-correct expectations for the data tables in
``src/tables.c``. Where Python diverges from ROM, the test is marked
``xfail`` with the gap ID so closure flips it to xpass.

See ``docs/parity/TABLES_C_AUDIT.md`` for the gap catalogue.
"""

from __future__ import annotations

import pytest

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    OffFlag,
    PlayerFlag,
    convert_flags_from_letters,
)

# ---------------------------------------------------------------------------
# Value-equivalence spot-checks — these PASS today.
# ---------------------------------------------------------------------------


def test_act_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:82-106`` letters A..dd map 1:1 to ``ActFlag`` bits."""
    assert int(ActFlag.IS_NPC) == 1 << 0  # A=npc
    assert int(ActFlag.AGGRESSIVE) == 1 << 5  # F=aggressive
    assert int(ActFlag.IS_HEALER) == 1 << 26  # aa=healer
    assert int(ActFlag.IS_CHANGER) == 1 << 29  # dd=changer


def test_player_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:108-128`` letters A..aa map 1:1 to ``PlayerFlag`` bits."""
    assert int(PlayerFlag.IS_NPC) == 1 << 0  # A=npc
    assert int(PlayerFlag.HOLYLIGHT) == 1 << 13  # N=holylight
    assert int(PlayerFlag.CANLOOT) == 1 << 15  # P=can_loot
    assert int(PlayerFlag.KILLER) == 1 << 26  # aa=killer


def test_off_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:163-186`` letters A..U map 1:1 to ``OffFlag`` bits."""
    assert int(OffFlag.AREA_ATTACK) == 1 << 0  # A=area_attack
    assert int(OffFlag.KICK_DIRT) == 1 << 9  # J=dirt_kick
    assert int(OffFlag.ASSIST_VNUM) == 1 << 20  # U=assist_vnum


def test_comm_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:271-296`` ``CommFlag`` bit positions match ``COMM_*``."""
    assert int(CommFlag.QUIET) == 1 << 0
    assert int(CommFlag.AFK) == 1 << 25


# ---------------------------------------------------------------------------
# TABLES-001 — AffectFlag bit positions diverge from ROM merc.h.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="TABLES-001: Python AffectFlag bit positions diverge from ROM merc.h "
    "(AFF_DETECT_GOOD=G=1<<6 in ROM, but AffectFlag.SANCTUARY=1<<6 in Python). "
    "Closure requires renumber + persistence migration. See TABLES_C_AUDIT.md.",
    strict=True,
)
def test_affect_flag_letters_match_rom_merc_h() -> None:
    """ROM ``src/merc.h:953-982`` letter-to-bit mapping for ``AFF_*``.

    Reproducer for TABLES-001. Decodes ROM letters via
    ``convert_flags_from_letters`` (which uses the ROM-correct A→0, G→6
    mapping) and asserts the resulting bits agree with the Python
    ``AffectFlag`` symbol that ROM names for that letter.
    """
    decoded_g = int(convert_flags_from_letters("G", AffectFlag))
    assert decoded_g == int(AffectFlag.DETECT_GOOD), (
        f"ROM G should be AFF_DETECT_GOOD; got {decoded_g:#x}, "
        f"AffectFlag.DETECT_GOOD={int(AffectFlag.DETECT_GOOD):#x}"
    )

    decoded_h = int(convert_flags_from_letters("H", AffectFlag))
    assert decoded_h == int(AffectFlag.SANCTUARY)

    decoded_z = int(convert_flags_from_letters("Z", AffectFlag))
    assert decoded_z == int(AffectFlag.DARK_VISION)

    decoded_dd = int(convert_flags_from_letters("dd", AffectFlag))
    assert decoded_dd == int(AffectFlag.SLOW)
