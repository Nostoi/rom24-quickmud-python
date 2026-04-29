"""ROM stat-bonus application tables (str_app, dex_app, con_app, wis_app).

Source of truth: src/const.c:728-878 (ROM 2.4b6).

ROM macro consumers (src/merc.h:2104-2110):

    #define GET_AC(ch, type) \
        ((ch)->armor[type] + (IS_AWAKE(ch) ? dex_app[get_curr_stat(ch, STAT_DEX)].defensive : 0))
    #define GET_HITROLL(ch) \
        ((ch)->hitroll + str_app[get_curr_stat(ch, STAT_STR)].tohit)
    #define GET_DAMROLL(ch) \
        ((ch)->damroll + str_app[get_curr_stat(ch, STAT_STR)].todam)

This module currently implements the ``get_hitroll`` accessor (CONST-002).
``get_damroll`` (CONST-003) and ``get_ac`` (CONST-004) will land alongside their
respective gap closures and reuse ``STR_APP`` / a future ``DEX_APP`` table.
"""

from __future__ import annotations

from typing import NamedTuple

from mud.models.constants import Stat


class StrAppRow(NamedTuple):
    """One row of ROM ``str_app[26]`` — see src/const.c:728-755."""

    tohit: int
    todam: int
    carry: int
    wield: int


# ROM src/const.c:728-755 — verbatim port of str_app[26].
STR_APP: tuple[StrAppRow, ...] = (
    StrAppRow(-5, -4, 0, 0),     # STR  0
    StrAppRow(-5, -4, 3, 1),     # STR  1
    StrAppRow(-3, -2, 3, 2),     # STR  2
    StrAppRow(-3, -1, 10, 3),    # STR  3
    StrAppRow(-2, -1, 25, 4),    # STR  4
    StrAppRow(-2, -1, 55, 5),    # STR  5
    StrAppRow(-1, 0, 80, 6),     # STR  6
    StrAppRow(-1, 0, 90, 7),     # STR  7
    StrAppRow(0, 0, 100, 8),     # STR  8
    StrAppRow(0, 0, 100, 9),     # STR  9
    StrAppRow(0, 0, 115, 10),    # STR 10
    StrAppRow(0, 0, 115, 11),    # STR 11
    StrAppRow(0, 0, 130, 12),    # STR 12
    StrAppRow(0, 0, 130, 13),    # STR 13
    StrAppRow(0, 1, 140, 14),    # STR 14
    StrAppRow(1, 1, 150, 15),    # STR 15
    StrAppRow(1, 2, 165, 16),    # STR 16
    StrAppRow(2, 3, 180, 22),    # STR 17
    StrAppRow(2, 3, 200, 25),    # STR 18
    StrAppRow(3, 4, 225, 30),    # STR 19
    StrAppRow(3, 5, 250, 35),    # STR 20
    StrAppRow(4, 6, 300, 40),    # STR 21
    StrAppRow(4, 6, 350, 45),    # STR 22
    StrAppRow(5, 7, 400, 50),    # STR 23
    StrAppRow(5, 8, 450, 55),    # STR 24
    StrAppRow(6, 9, 500, 60),    # STR 25
)


def _curr_str(ch) -> int:
    """Return ch's current STR clamped to the str_app index range [0, 25]."""

    getter = getattr(ch, "get_curr_stat", None)
    if getter is None:
        raw = getattr(ch, "perm_stat", None)
        if not raw:
            return 13  # ROM neutral default — tohit/todam columns are 0 here
        idx = int(Stat.STR)
        return max(0, min(25, int(raw[idx]) if idx < len(raw) else 13))
    val = getter(Stat.STR)
    if val is None:
        return 13
    return max(0, min(25, int(val)))


def get_hitroll(ch) -> int:
    """Return ROM ``GET_HITROLL(ch)``: ch.hitroll + str_app[STR].tohit.

    Mirrors src/merc.h:2107-2108. Consumed at src/fight.c:471 for the
    THAC0 to-hit calculation.
    """

    base = int(getattr(ch, "hitroll", 0) or 0)
    return base + STR_APP[_curr_str(ch)].tohit
