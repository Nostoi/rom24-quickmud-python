"""Integration tests for ROM advance_level practice gain via wis_app[WIS].practice.

Mirrors ROM src/update.c:87 — `add_prac = wis_app[get_curr_stat(ch, STAT_WIS)].practice;`
then `ch->practice += add_prac;`. No `* 9 / 10`, no UMAX floor — practices
flow directly from the table.

Closes CONST-006 (wis_app practice add-on).

Reference values from src/const.c:790-817:
    WIS  0..4  -> 0
    WIS  5..14 -> 1
    WIS 15..17 -> 2
    WIS 18..21 -> 3
    WIS 22..24 -> 4
    WIS 25     -> 5
"""

from __future__ import annotations

import pytest

from mud.advancement import advance_level
from mud.math.stat_apps import WIS_APP, wis_practice_bonus
from mud.models.character import Character, PCData
from mud.models.constants import Stat
from mud.utils import rng_mm


def _make_pc(*, wis: int, ch_class: int = 0) -> Character:
    char = Character(
        name=f"Cls{ch_class}Wis{wis}",
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
    char.perm_stat[Stat.WIS] = wis
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


# ---------------------------------------------------------------------------
# WIS_APP table verification (src/const.c:790-817)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wis, expected",
    [
        (0, 0), (3, 0), (4, 0),
        (5, 1), (10, 1), (14, 1),
        (15, 2), (17, 2),
        (18, 3), (21, 3),
        (22, 4), (24, 4),
        (25, 5),
    ],
)
def test_wis_app_practice_column(wis: int, expected: int) -> None:
    assert WIS_APP[wis].practice == expected


def test_wis_app_table_length() -> None:
    assert len(WIS_APP) == 26


# ---------------------------------------------------------------------------
# wis_practice_bonus accessor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wis, expected", [(3, 0), (13, 1), (18, 3), (25, 5)])
def test_wis_practice_bonus_reads_curr_stat(wis: int, expected: int) -> None:
    char = _make_pc(wis=wis)
    assert wis_practice_bonus(char) == expected


def test_wis_practice_bonus_respects_mod_stat() -> None:
    """`get_curr_stat` honors mod_stat buffs."""

    char = _make_pc(wis=18)
    char.mod_stat[Stat.WIS] = 7  # 18 + 7 = 25 → cap at 25 → practice 5
    assert wis_practice_bonus(char) == 5


# ---------------------------------------------------------------------------
# advance_level practice integration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wis, expected_practices",
    [
        (3, 0),    # WIS-3 dunce: gains zero practices per level (ROM)
        (13, 1),   # default
        (18, 3),
        (25, 5),
    ],
)
def test_advance_level_grants_wis_app_practices(wis: int, expected_practices: int) -> None:
    rng_mm.seed_mm(54321)
    char = _make_pc(wis=wis)
    advance_level(char)
    assert char.practice == expected_practices


def test_advance_level_practice_message_uses_actual_value() -> None:
    """ROM "You gain ... N practice(s)" reflects wis_app value, not a constant."""

    rng_mm.seed_mm(54321)
    char = _make_pc(wis=25)  # +5 practices
    advance_level(char)
    # WIS-25 → 5 practices; 5 != 1 so 'practices' (plural)
    assert any("5 practice" in msg for msg in char.messages)


def test_advance_level_low_wis_shows_singular_zero() -> None:
    """WIS-3 mage gets 0 practices → message must still match ROM pluralisation."""

    rng_mm.seed_mm(54321)
    char = _make_pc(wis=3)
    advance_level(char)
    assert any("0 practices" in msg for msg in char.messages)


def test_train_still_constant_one_per_level() -> None:
    """ROM `ch->train += 1` is unchanged — only `add_prac` is wis-driven."""

    rng_mm.seed_mm(54321)
    char = _make_pc(wis=25)
    advance_level(char)
    assert char.train == 1
