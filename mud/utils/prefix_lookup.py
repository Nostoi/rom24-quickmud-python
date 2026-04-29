"""ROM-faithful prefix-match name lookup.

Mirrors ROM `str_prefix(short, full)` semantics (returns 0 when `short` is
a case-insensitive prefix of `full`) as used throughout `src/lookup.c` and
`src/bit.c:flag_lookup`.

Use this anywhere ROM accepts an abbreviation: flag names, race names,
class names, position/sex/size/item-type names, etc.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import IntFlag
from typing import TypeVar

T = TypeVar("T")


def prefix_lookup_index(name: str | None, candidates: Iterable[str]) -> int:
    """Return the index of the first candidate whose name is prefix-matched.

    Mirrors ROM `src/lookup.c` family (e.g. `race_lookup`, `position_lookup`).
    Case-insensitive; accepts ``name`` when it is a prefix of any candidate.
    Returns ``-1`` on no match — callers map that to whatever sentinel ROM
    returns for their specific table (-1, 0, NO_FLAG, etc.).
    """
    if not name:
        return -1
    needle = name.lower()
    for index, candidate in enumerate(candidates):
        if not candidate:
            continue
        if candidate.lower().startswith(needle):
            return index
    return -1


def prefix_lookup_intflag(name: str | None, flag_enum: type[IntFlag]) -> int | None:
    """Return the int bit value of the first IntFlag member prefix-matched.

    Mirrors ROM `flag_lookup(name, flag_table)` (src/bit.c). Returns ``None``
    on no match — callers map that to ROM's ``NO_FLAG`` semantics.
    """
    if not name:
        return None
    needle = name.lower()
    for member in flag_enum.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return None


def sex_lookup(name: str | None) -> int:
    """Return the int Sex index whose name is prefix-matched by *name*.

    Mirrors ROM ``sex_lookup`` (src/lookup.c:81-93). Returns ``-1`` on miss.
    """
    # mirroring ROM src/lookup.c:81-93 — sex_lookup uses str_prefix.
    from mud.models.constants import Sex

    if not name:
        return -1
    needle = name.lower()
    for member in Sex.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1


def position_lookup(name: str | None) -> int:
    """Return the int Position index whose name is prefix-matched by *name*.

    Mirrors ROM ``position_lookup`` (src/lookup.c:67-79):
    case-insensitive prefix-match against the position table. Returns ``-1``
    on no match (ROM fall-through).
    """
    # mirroring ROM src/lookup.c:67-79 — position_lookup uses str_prefix.
    from mud.models.constants import Position

    if not name:
        return -1
    needle = name.lower()
    for member in Position.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1
