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


class DexAppRow(NamedTuple):
    """One row of ROM ``dex_app[26]`` — see src/const.c:821-848."""

    defensive: int


class ConAppRow(NamedTuple):
    """One row of ROM ``con_app[26]`` — see src/const.c:850-878.

    The ``shock`` column is defined but unused by ROM (verified by `grep -rn
    "con_app" src/`); only `update.c:78` reads `con_app[CON].hitp` in
    `advance_level`. We port both columns for completeness; only `hitp`
    has a live consumer in Python.
    """

    hitp: int
    shock: int


# ROM src/const.c:821-848 — verbatim port of dex_app[26].
DEX_APP: tuple[DexAppRow, ...] = (
    DexAppRow(60),    # DEX  0
    DexAppRow(50),    # DEX  1
    DexAppRow(50),    # DEX  2
    DexAppRow(40),    # DEX  3
    DexAppRow(30),    # DEX  4
    DexAppRow(20),    # DEX  5
    DexAppRow(10),    # DEX  6
    DexAppRow(0),     # DEX  7
    DexAppRow(0),     # DEX  8
    DexAppRow(0),     # DEX  9
    DexAppRow(0),     # DEX 10
    DexAppRow(0),     # DEX 11
    DexAppRow(0),     # DEX 12
    DexAppRow(0),     # DEX 13
    DexAppRow(0),     # DEX 14
    DexAppRow(-10),   # DEX 15
    DexAppRow(-15),   # DEX 16
    DexAppRow(-20),   # DEX 17
    DexAppRow(-30),   # DEX 18
    DexAppRow(-40),   # DEX 19
    DexAppRow(-50),   # DEX 20
    DexAppRow(-60),   # DEX 21
    DexAppRow(-75),   # DEX 22
    DexAppRow(-90),   # DEX 23
    DexAppRow(-105),  # DEX 24
    DexAppRow(-120),  # DEX 25
)


# ROM src/const.c:850-878 — verbatim port of con_app[26].
CON_APP: tuple[ConAppRow, ...] = (
    ConAppRow(-4, 20),   # CON  0
    ConAppRow(-3, 25),   # CON  1
    ConAppRow(-2, 30),   # CON  2
    ConAppRow(-2, 35),   # CON  3
    ConAppRow(-1, 40),   # CON  4
    ConAppRow(-1, 45),   # CON  5
    ConAppRow(-1, 50),   # CON  6
    ConAppRow(0, 55),    # CON  7
    ConAppRow(0, 60),    # CON  8
    ConAppRow(0, 65),    # CON  9
    ConAppRow(0, 70),    # CON 10
    ConAppRow(0, 75),    # CON 11
    ConAppRow(0, 80),    # CON 12
    ConAppRow(0, 85),    # CON 13
    ConAppRow(0, 88),    # CON 14
    ConAppRow(1, 90),    # CON 15
    ConAppRow(2, 95),    # CON 16
    ConAppRow(2, 97),    # CON 17
    ConAppRow(3, 99),    # CON 18
    ConAppRow(3, 99),    # CON 19
    ConAppRow(4, 99),    # CON 20
    ConAppRow(4, 99),    # CON 21
    ConAppRow(5, 99),    # CON 22
    ConAppRow(6, 99),    # CON 23
    ConAppRow(7, 99),    # CON 24
    ConAppRow(8, 99),    # CON 25
)


def _curr_stat(ch, stat: Stat, default: int = 13) -> int:
    """Return ch's current stat clamped to the app-table index range [0, 25]."""

    getter = getattr(ch, "get_curr_stat", None)
    if getter is None:
        raw = getattr(ch, "perm_stat", None)
        if not raw:
            return default
        idx = int(stat)
        return max(0, min(25, int(raw[idx]) if idx < len(raw) else default))
    val = getter(stat)
    if val is None:
        return default
    return max(0, min(25, int(val)))


def _curr_str(ch) -> int:
    """Return ch's current STR clamped to the str_app index range [0, 25]."""

    return _curr_stat(ch, Stat.STR)


def _curr_dex(ch) -> int:
    """Return ch's current DEX clamped to the dex_app index range [0, 25]."""

    return _curr_stat(ch, Stat.DEX)


def _curr_con(ch) -> int:
    """Return ch's current CON clamped to the con_app index range [0, 25]."""

    return _curr_stat(ch, Stat.CON)


def _is_awake(ch) -> bool:
    """ROM IS_AWAKE: position > POS_SLEEPING (4). See src/merc.h:2103."""

    pos = getattr(ch, "position", 8)
    try:
        return int(pos) > 4
    except (TypeError, ValueError):
        return True


def get_hitroll(ch) -> int:
    """Return ROM ``GET_HITROLL(ch)``: ch.hitroll + str_app[STR].tohit.

    Mirrors src/merc.h:2107-2108. Consumed at src/fight.c:471 for the
    THAC0 to-hit calculation.
    """

    base = int(getattr(ch, "hitroll", 0) or 0)
    return base + STR_APP[_curr_str(ch)].tohit


def get_damroll(ch) -> int:
    """Return ROM ``GET_DAMROLL(ch)``: ch.damroll + str_app[STR].todam.

    Mirrors src/merc.h:2109-2110. Consumed at src/fight.c:588 for the
    weapon damage contribution.
    """

    base = int(getattr(ch, "damroll", 0) or 0)
    return base + STR_APP[_curr_str(ch)].todam


def get_ac(ch, ac_type: int) -> int:
    """Return ROM ``GET_AC(ch, type)``: armor[type] + (IS_AWAKE ? dex_app[DEX].defensive : 0).

    Mirrors src/merc.h:2104-2106. Consumed at src/fight.c:480-489 for combat
    AC, src/act_info.c:1591-1650 for the score AC tier display, and
    src/act_wiz.c:1612-1613 for the wiz "stat char" AC line.

    Sleeping/stunned/incap/dead victims do NOT receive the DEX defensive
    bonus — IS_AWAKE is ``position > POS_SLEEPING``.
    """

    armor = getattr(ch, "armor", None)
    if armor is None or ac_type < 0 or ac_type >= len(armor):
        base = 0
    else:
        base = int(armor[ac_type])
    if not _is_awake(ch):
        return base
    return base + DEX_APP[_curr_dex(ch)].defensive


def con_hitp_bonus(ch) -> int:
    """Return ROM ``con_app[get_curr_stat(ch, STAT_CON)].hitp``.

    Mirrors src/const.c:850-878. Consumed at src/update.c:74-79
    (advance_level per-level HP gain).
    """

    return CON_APP[_curr_con(ch)].hitp
