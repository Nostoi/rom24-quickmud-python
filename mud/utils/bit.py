"""Port of ROM `src/bit.c` helpers (BIT-001, BIT-002, BIT-003).

Where ROM uses ``struct flag_type *`` table pointers, the Python port takes
either an ``IntFlag`` class (ROM "flag" table) or an ``IntEnum`` class
(ROM "stat" table). Stat-vs-flag classification is encoded by the type
itself, replacing ROM's ``flag_stat_table[]`` registry (BIT-003).
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

from mud.utils.prefix_lookup import prefix_lookup_intflag


def flag_value(table: type, argument: str) -> int | None:
    """Return the int value(s) of the named flag(s) in *table*.

    Mirrors ROM ``flag_value`` (src/bit.c:111-142):

    - When *table* is an ``IntFlag`` (ROM "flag" table): tokenize *argument*,
      prefix-look-up each token via ``prefix_lookup_intflag``, OR every hit
      into ``marked``. Skip unknown tokens silently.
    - When *table* is an ``IntEnum`` (ROM "stat" table): return the single
      ``int(member)`` whose name prefix-matches *argument* — ROM's
      ``is_stat`` branch returns ``flag_lookup(argument, table)`` directly.

    Returns ``None`` (the ROM ``NO_FLAG`` sentinel; ROM uses ``-1``) when
    nothing matched.
    """

    if not argument:
        return None

    if isinstance(table, type) and issubclass(table, IntFlag):
        marked = 0
        found = False
        for token in argument.split():
            bit = prefix_lookup_intflag(token, table)
            if bit is not None:
                marked |= bit
                found = True
        return marked if found else None

    if isinstance(table, type) and issubclass(table, IntEnum):
        # mirrors ROM src/bit.c:118-119 — stat tables return a single value.
        # ROM `flag_lookup(argument, table)` matches the entire argument
        # string against table names; we mirror that by matching the first
        # whitespace-delimited token.
        first = argument.split(None, 1)[0] if argument.strip() else ""
        if not first:
            return None
        needle = first.lower()
        for member in table.__members__.values():
            if member.name and member.name.lower().startswith(needle):
                return int(member)
        return None

    raise TypeError(f"flag_value: unsupported table type {table!r}; expected IntFlag or IntEnum subclass")


def flag_string(table: type, bits: int) -> str:
    """Return a space-joined string of every flag name set in *bits*.

    Mirrors ROM ``flag_string`` (src/bit.c:151-177):

    - When *table* is an ``IntFlag`` (ROM "flag" table): for each member
      whose bit is set in *bits*, append the lowercase name; join with
      single spaces (ROM strips the leading space at return).
    - When *table* is an ``IntEnum`` (ROM "stat" table): return the single
      lowercase name whose value equals *bits*; ROM ``break``s on the
      first match.
    - Returns the literal ``"none"`` when nothing matched.

    The ROM rotating two-buffer trick (``buf[2][512]``, ``cnt`` toggled)
    is unnecessary in Python because strings are immutable.
    """

    if isinstance(table, type) and issubclass(table, IntFlag):
        names: list[str] = []
        for member in table.__members__.values():
            value = int(member)
            if value == 0:
                continue
            # Only emit single-bit members; composite alias members would
            # double-print. ROM tables are pure single-bit anyway.
            if value & (value - 1) != 0:
                continue
            if (bits & value) == value:
                names.append(member.name.lower())
        return " ".join(names) if names else "none"

    if isinstance(table, type) and issubclass(table, IntEnum):
        # mirrors ROM src/bit.c:169-174 — stat table: equality match, then break.
        for member in table.__members__.values():
            if int(member) == bits:
                return member.name.lower()
        return "none"

    raise TypeError(f"flag_string: unsupported table type {table!r}; expected IntFlag or IntEnum subclass")
