"""BIT-001 — `flag_value(table, argument)` helper.

Mirrors ROM `src/bit.c:111-142`. Tokenizes the argument string and looks up
each token in the supplied flag table; OR's hits for `IntFlag` (flag) tables
and returns a single matched value for `IntEnum` (stat) tables. Returns
``None`` when nothing matches (ROM `NO_FLAG` = -1).
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

from mud.utils.bit import flag_value
from mud.models.constants import ActFlag, Position


class _StatTable(IntEnum):
    ALPHA = 0
    BRAVO = 1
    CHARLIE = 2


class _FlagTable(IntFlag):
    ALPHA = 0x01
    BRAVO = 0x02
    CHARLIE = 0x04


def test_flag_value_returns_none_on_empty_argument() -> None:
    # mirrors ROM src/bit.c:138-141 — `found == FALSE` -> NO_FLAG.
    assert flag_value(_FlagTable, "") is None
    assert flag_value(_FlagTable, "   ") is None


def test_flag_value_returns_none_on_no_match() -> None:
    assert flag_value(_FlagTable, "doesnotexist") is None


def test_flag_value_intflag_single_token() -> None:
    assert flag_value(_FlagTable, "alpha") == int(_FlagTable.ALPHA)


def test_flag_value_intflag_or_accumulates_multiple_tokens() -> None:
    # mirrors ROM src/bit.c:124-136 — OR every match into `marked`.
    result = flag_value(_FlagTable, "alpha bravo")
    assert result == int(_FlagTable.ALPHA | _FlagTable.BRAVO)


def test_flag_value_intflag_skips_unknown_tokens() -> None:
    # mirrors ROM src/bit.c:131-135 — unknown tokens are silently skipped
    # (different from ROM `do_flag`, which bails on the first unknown).
    result = flag_value(_FlagTable, "alpha bogus charlie")
    assert result == int(_FlagTable.ALPHA | _FlagTable.CHARLIE)


def test_flag_value_intflag_prefix_match() -> None:
    # mirrors ROM `flag_lookup` -> `str_prefix`.
    assert flag_value(_FlagTable, "al") == int(_FlagTable.ALPHA)


def test_flag_value_stat_table_returns_single_value_no_accumulation() -> None:
    # mirrors ROM src/bit.c:118-119 — `is_stat` -> single `flag_lookup`.
    # Even when multiple tokens are passed, an IntEnum (stat) table returns
    # only the first match.
    assert flag_value(_StatTable, "bravo") == int(_StatTable.BRAVO)
    # Multi-token argument: ROM `flag_lookup` only sees the first token
    # ("alpha bravo" -> "alpha bravo" is treated as one literal name);
    # mirroring ROM, we delegate the first-token-only behavior.
    assert flag_value(_StatTable, "alpha extra") == int(_StatTable.ALPHA)


def test_flag_value_real_act_flags_table_intflag_accumulates() -> None:
    result = flag_value(ActFlag, "sentinel scavenger")
    assert result is not None
    assert result & int(ActFlag.SENTINEL)
    assert result & int(ActFlag.SCAVENGER)


def test_flag_value_real_position_intenum_returns_single() -> None:
    result = flag_value(Position, "standing")
    assert result == int(Position.STANDING)
