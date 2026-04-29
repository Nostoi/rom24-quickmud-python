"""BIT-002 — `flag_string(table, bits)` helper.

Mirrors ROM `src/bit.c:151-177`. Returns a space-joined string of every
flag-name set in *bits* (for IntFlag tables) or the single name whose
value equals *bits* (for IntEnum stat tables). Returns the literal
``"none"`` when nothing matched.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

from mud.models.constants import ActFlag, Position
from mud.utils.bit import flag_string


class _StatTable(IntEnum):
    ALPHA = 0
    BRAVO = 1
    CHARLIE = 2


class _FlagTable(IntFlag):
    ALPHA = 0x01
    BRAVO = 0x02
    CHARLIE = 0x04


def test_flag_string_returns_none_literal_on_zero_bits() -> None:
    # mirrors ROM src/bit.c:176 — `(buf[cnt][0] != '\0') ? ... : "none"`.
    assert flag_string(_FlagTable, 0) == "none"


def test_flag_string_intflag_single_bit() -> None:
    assert flag_string(_FlagTable, int(_FlagTable.BRAVO)) == "bravo"


def test_flag_string_intflag_multiple_bits_space_joined() -> None:
    bits = int(_FlagTable.ALPHA | _FlagTable.CHARLIE)
    # mirrors ROM src/bit.c:162-168 — iterate table, append " "+name on each
    # IS_SET hit; the leading space is stripped on return.
    assert flag_string(_FlagTable, bits) == "alpha charlie"


def test_flag_string_intflag_unknown_bits_yield_none() -> None:
    # 0x40 is not in _FlagTable — no name matches, ROM returns "none".
    assert flag_string(_FlagTable, 0x40) == "none"


def test_flag_string_stat_table_single_match() -> None:
    # mirrors ROM src/bit.c:169-174 — stat table: one match by equality, then break.
    assert flag_string(_StatTable, int(_StatTable.BRAVO)) == "bravo"


def test_flag_string_stat_table_no_match_returns_none() -> None:
    assert flag_string(_StatTable, 99) == "none"


def test_flag_string_real_act_flags_table() -> None:
    bits = int(ActFlag.SENTINEL | ActFlag.SCAVENGER)
    result = flag_string(ActFlag, bits)
    # Order is dictated by ROM table iteration order; both names present.
    tokens = result.split()
    assert "sentinel" in tokens
    assert "scavenger" in tokens


def test_flag_string_real_position_intenum() -> None:
    assert flag_string(Position, int(Position.STANDING)) == "standing"
