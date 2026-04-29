"""BIT-003 — `is_stat(table)` helper.

Mirrors ROM `src/bit.c:50-104` (`flag_stat_table[]` registry + `is_stat()`).
ROM partitions every flag table into "stat" (single-value enum, e.g.
`sex_flags`, `position_flags`) vs "flag" (bitmask, e.g. `act_flags`,
`affect_flags`). The Python port encodes this in the type system:
``IntEnum`` = stat, ``IntFlag`` = flag.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    PlayerFlag,
    Position,
    Sex,
    Sector,
)
from mud.utils.bit import is_stat


def test_is_stat_true_for_intenum_stat_tables() -> None:
    # mirrors ROM src/bit.c:53-57 — sex_flags, sector_flags, position_flags
    # all have `stat == TRUE` in flag_stat_table[].
    assert is_stat(Sex) is True
    assert is_stat(Sector) is True
    assert is_stat(Position) is True


def test_is_stat_false_for_intflag_flag_tables() -> None:
    # mirrors ROM src/bit.c:52,61,62 — area_flags, act_flags, affect_flags
    # all have `stat == FALSE` in flag_stat_table[].
    assert is_stat(ActFlag) is False
    assert is_stat(AffectFlag) is False
    assert is_stat(PlayerFlag) is False


def test_is_stat_handles_local_intenum_intflag_subclasses() -> None:
    class StatLocal(IntEnum):
        A = 0
        B = 1

    class FlagLocal(IntFlag):
        A = 0x1
        B = 0x2

    assert is_stat(StatLocal) is True
    assert is_stat(FlagLocal) is False


def test_is_stat_false_for_non_enum_types() -> None:
    # mirrors ROM `is_stat` returning FALSE for unknown tables.
    assert is_stat(int) is False
    assert is_stat(str) is False


def test_is_stat_false_for_non_type_arguments() -> None:
    assert is_stat(42) is False
    assert is_stat("not a table") is False
    assert is_stat(None) is False
