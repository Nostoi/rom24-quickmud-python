"""Integration tests for ROM advance_level HP roll + con_app[CON].hitp.

Mirrors ROM src/update.c:74-79:

    add_hp = con_app[get_curr_stat(ch, STAT_CON)].hitp
           + number_range(class_table[ch->class].hp_min,
                          class_table[ch->class].hp_max);
    add_hp = add_hp * 9 / 10;
    add_hp = UMAX(2, add_hp);

Closes CONST-005 (HP path only — wis_app practice and mana/move RNG are
separate gaps).

Notes:
- The autouse `_seed_rng` fixture in tests/integration/conftest.py seeds
  rng_mm to 12345 before this test runs. Tests below override that seed
  with `rng_mm.seed_mm(<known seed>)` to pin specific number_range
  outcomes.
- ROM `class_table[mage].hp_min/hp_max == 6/8`, `[cleric] 7/10`,
  `[thief] 8/13`, `[warrior] 11/15` (src/const.c:394-419).
- ROM `con_app[CON].hitp` for CON-3..25 is the load-bearing column;
  CON-3 = -2 hitp, CON-13 = 0 hitp, CON-25 = +8 hitp (src/const.c:850-878).
"""

from __future__ import annotations

import pytest

from mud.advancement import advance_level
from mud.math.c_compat import c_div
from mud.math.stat_apps import CON_APP, con_hitp_bonus
from mud.models.character import Character, PCData
from mud.models.classes import CLASS_TABLE
from mud.models.constants import Stat
from mud.utils import rng_mm


def _make_pc(*, ch_class: int, con: int) -> Character:
    """Build a PC at level 1 with the given class and CON, neutral on others."""

    char = Character(
        name=f"Cls{ch_class}Con{con}",
        ch_class=ch_class,
        is_npc=False,
        pcdata=PCData(),
        max_hit=20,
        max_mana=20,
        max_move=20,
        practice=0,
        train=0,
    )
    char.perm_stat = [13, 13, 13, 13, 13]
    char.perm_stat[Stat.CON] = con
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


# ---------------------------------------------------------------------------
# CON_APP table verification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "con, expected_hitp",
    [
        (3, -2),
        (8, 0),
        (13, 0),
        (15, 1),
        (18, 3),
        (20, 4),
        (25, 8),
    ],
)
def test_con_hitp_bonus_matches_rom_table(con: int, expected_hitp: int) -> None:
    """con_app[CON].hitp values must match ROM src/const.c:850-878."""

    char = _make_pc(ch_class=3, con=con)
    assert CON_APP[con].hitp == expected_hitp
    assert con_hitp_bonus(char) == expected_hitp


# ---------------------------------------------------------------------------
# advance_level HP path
# ---------------------------------------------------------------------------


def _expected_hp_gain(ch_class: int, con: int, hp_roll: int) -> int:
    """Mirror ROM src/update.c:74-79 closed form for a known number_range outcome."""

    add_hp = CON_APP[con].hitp + hp_roll
    add_hp = c_div(add_hp * 9, 10)
    return max(2, add_hp)


@pytest.mark.parametrize("ch_class", [0, 1, 2, 3])
def test_advance_level_hp_uses_class_table_range_and_con_app(
    ch_class: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """advance_level must roll number_range(class.hp_min, class.hp_max) and add con_app[CON].hitp.

    Pins number_range to always return ``hp_min`` and asserts the resulting
    HP gain matches the ROM closed form for both CON-3 and CON-25.
    """

    cls = CLASS_TABLE[ch_class]
    expected_lo = cls.hp_min

    captured: list[tuple[int, int]] = []

    def pinned_range(lo: int, hi: int) -> int:
        captured.append((lo, hi))
        return lo

    monkeypatch.setattr(rng_mm, "number_range", pinned_range)

    weak = _make_pc(ch_class=ch_class, con=3)
    strong = _make_pc(ch_class=ch_class, con=25)
    weak_pre, strong_pre = weak.max_hit, strong.max_hit

    advance_level(weak)
    advance_level(strong)

    # number_range MUST be called with (hp_min, hp_max).
    assert (cls.hp_min, cls.hp_max) in captured

    weak_gain = weak.max_hit - weak_pre
    strong_gain = strong.max_hit - strong_pre
    assert weak_gain == _expected_hp_gain(ch_class, con=3, hp_roll=expected_lo)
    assert strong_gain == _expected_hp_gain(ch_class, con=25, hp_roll=expected_lo)


def test_advance_level_hp_minimum_floor_is_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """ROM UMAX(2, add_hp) — even a maximally penalized roll yields >= 2 HP.

    With CON-0 (con_app.hitp == -4), mage hp_min == 6, the raw add_hp is
    (-4 + 6) * 9 / 10 == 18 / 10 == 1 (c_div), which UMAX(2, ...) lifts to 2.
    """

    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: lo)

    char = _make_pc(ch_class=0, con=0)  # mage
    pre = char.max_hit
    advance_level(char)
    assert char.max_hit - pre == 2


def test_advance_level_hp_uses_get_curr_stat_for_con(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CON read must respect mod_stat (buffs/debuffs), not just perm_stat.

    Sets perm_stat CON=13 (hitp=0) and mod_stat CON=+5 → effective CON=18
    (hitp=3). With pinned number_range == hp_min, the gain must reflect
    the buffed CON, not the base.
    """

    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: lo)

    char = _make_pc(ch_class=0, con=13)  # mage, hp_min=6
    char.mod_stat = [0, 0, 0, 0, 5]  # +5 CON → effective 18
    pre = char.max_hit
    advance_level(char)
    # con_app[18].hitp == 3, hp_roll == 6, (3 + 6) * 9 / 10 == 8
    assert char.max_hit - pre == 8


def test_advance_level_perm_hit_tracks_max_hit_increase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ROM src/update.c:84 also adds add_hp to pcdata->perm_hit."""

    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: hi)

    char = _make_pc(ch_class=3, con=15)  # warrior hp_max=15, con_app[15].hitp=1
    pre_max = char.max_hit
    pre_perm = char.pcdata.perm_hit
    advance_level(char)
    delta = char.max_hit - pre_max
    assert char.pcdata.perm_hit - pre_perm == delta
