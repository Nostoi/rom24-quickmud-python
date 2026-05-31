"""ARITH-105 — `Character.get_curr_stat` must floor at 3, not 0.

Mirrors ROM `src/handler.c:872`:

    return URANGE (3, ch->perm_stat[stat] + ch->mod_stat[stat], max);

ROM's `URANGE(3, ..., max)` guarantees no character (PC or NPC) ever
reads a current stat below 3. Pre-fix Python used `max(0, min(25, total))`
at `mud/models/character.py:478`, which let stacked debuffs drive a
character's effective STR/INT/WIS/DEX/CON to 0–2. That value then flowed
into every stat-dependent calculation: hit/dam apps (str_app, dex_app),
AC defensive (dex_app), CON regen (con_app), INT learn rate, WIS
practice gain, carry capacity, wield strength check, hide/sneak rolls.

Scope: this test covers only the **floor** (3) — the ceiling divergence
(Python uses flat `min(25, ...)`; ROM uses race/class-specific
`max_stat` for PCs and only 25 for NPCs/immortals) is tracked
separately as ARITH-114.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, PCData
from mud.models.constants import Stat
from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance


def _make_pc() -> Character:
    char = Character(
        name="FloorPC",
        ch_class=0,
        is_npc=False,
        pcdata=PCData(),
        max_hit=20,
        max_mana=20,
        max_move=20,
    )
    char.perm_stat = [13, 13, 13, 13, 13]
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


def _make_npc() -> MobInstance:
    mob = MobInstance(
        name="FloorMob",
        level=1,
        current_hp=20,
        prototype=MobIndex(vnum=9901, short_descr="floor mob"),
        max_hit=20,
    )
    mob.perm_stat = [13, 13, 13, 13, 13]
    mob.mod_stat = [0, 0, 0, 0, 0]
    return mob


@pytest.mark.parametrize("stat", [Stat.STR, Stat.INT, Stat.WIS, Stat.DEX, Stat.CON])
def test_get_curr_stat_floors_at_three_when_heavily_debuffed(stat: Stat) -> None:
    """Stacked debuffs that would drop perm+mod below 3 must read as 3."""

    char = _make_pc()
    char.mod_stat[int(stat)] = -15  # perm 13 + mod -15 = -2 raw

    assert char.get_curr_stat(stat) == 3


@pytest.mark.parametrize("stat", [Stat.STR, Stat.INT, Stat.WIS, Stat.DEX, Stat.CON])
def test_get_curr_stat_floors_at_three_for_exactly_zero(stat: Stat) -> None:
    """perm + mod == 0 → floor to 3 (ROM URANGE)."""

    char = _make_pc()
    char.mod_stat[int(stat)] = -13  # perm 13 + mod -13 = 0 raw

    assert char.get_curr_stat(stat) == 3


@pytest.mark.parametrize("stat", [Stat.STR, Stat.INT, Stat.WIS, Stat.DEX, Stat.CON])
def test_get_curr_stat_floor_unchanged_when_total_already_at_three(stat: Stat) -> None:
    """perm + mod == 3 already → returns 3 exactly."""

    char = _make_pc()
    char.perm_stat[int(stat)] = 3
    char.mod_stat[int(stat)] = 0

    assert char.get_curr_stat(stat) == 3


def test_get_curr_stat_positive_buff_unchanged() -> None:
    """Positive buff inside [3, 25] passes through unmodified."""

    char = _make_pc()
    char.mod_stat[int(Stat.STR)] = 2  # 13 + 2 = 15

    assert char.get_curr_stat(Stat.STR) == 15


def test_get_curr_stat_ceiling_still_at_twenty_five() -> None:
    """Ceiling clamp at 25 unchanged by floor fix."""

    char = _make_pc()
    char.perm_stat[int(Stat.STR)] = 18
    char.mod_stat[int(Stat.STR)] = 10  # 28 raw → clamp 25

    assert char.get_curr_stat(Stat.STR) == 25


@pytest.mark.parametrize("stat", [Stat.STR, Stat.INT, Stat.WIS, Stat.DEX, Stat.CON])
def test_mob_get_curr_stat_floors_at_three_when_raw_total_is_lower(stat: Stat) -> None:
    """NPCs use the same ROM floor as PCs.

    # mirrors ROM src/handler.c:868-874 — get_curr_stat uses URANGE(3, ..., max)
    # for IS_NPC(ch) too.
    """

    mob = _make_npc()
    mob.mod_stat[int(stat)] = -15  # perm 13 + mod -15 = -2 raw

    assert mob.get_curr_stat(stat) == 3


def test_mob_get_curr_stat_floors_directly_constructed_zero_stat() -> None:
    """Directly constructed test mobs still follow ROM's lower clamp."""

    mob = _make_npc()
    mob.perm_stat[int(Stat.STR)] = 0

    assert mob.get_curr_stat(Stat.STR) == 3
